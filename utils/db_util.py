#!/usr/bin/python
import logging
import time
from bottle import abort
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import ConflictError

class DBUtil(object):
    """This class provides helper methods to be used in Efetch and its plugins"""
    elasticsearch = None

    def __init__(self, es_url=None):
        """Creates the Efetch indices in Elasticsearch if they do not exist"""
        if es_url:
            self.elasticsearch = Elasticsearch([es_url])
        else:
            self.elasticsearch = Elasticsearch()
   
        #Elastic Search Setup
        self.elasticsearch.indices.create(index='efetch-config',ignore=400)
        self.elasticsearch.indices.create(index='efetch-log',ignore=400)
        self.elasticsearch.indices.create(index='efetch-cases',ignore=400)
        self.elasticsearch.indices.create(index='efetch_image_ids',ignore=400)
        self.elasticsearch.indices.create(index='efetch_evidence',ignore=400)
        self.elasticsearch.indices.put_template(name="efetch-case", body=case_template())
        self.elasticsearch.indices.put_template(name="efetch_evidence", body=evidence_template())
        self.elasticsearch.indices.put_template(name="efetch-image_ids", body=image_id_template())

    def get_file_from_pid(self, pid, abort_on_error=True):
        """Returns the file object for the given file in the database"""
        return self.get_file(pid.split('/')[0], pid, abort_on_error)
   
    def query(self, query, image_id):
        """Returns the results of an Elastic Search query without error checking"""
        return self.elasticsearch.search(index='efetch_evidence_' + image_id, body=query)

    def bool_query(self, directory, bool_query = {}, size=10000, use_directory=True):
        """Returns the results of an Elastic Search boolean query within a given directory"""
        #REF: https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-bool-query.html
        #TODO: Loop through if size > 10000
        bool_query = self.append_dict(bool_query, 'must', { 'term': { 'dir': directory['pid'] + '/' } })
        query = { 'query': { 'bool': bool_query, }, 'size': size} 
        return self.elasticsearch.search(index='efetch_evidence_' + directory['image_id'], body=query)

    def bool_query_evidence(self, directory, bool_query = {}, size=10000):
        """Returns a list of evidence for an Elastic Search boolean query within a directory"""
        bool_query = self.append_dict(bool_query, 'must', {'term': {'parser': 'efetch'}})
        result = self.bool_query(directory, bool_query, size)
        return [(evidence['_source']) for evidence in result['hits']['hits']]

    def append_dict(self, dictionary, key, value):
        """Appends values to a dictionary in the format Elasticsearch expects"""
        if not dictionary:
            dictionary = {}
        if not key in dictionary:
            dictionary[key] = value
        elif isinstance(dictionary[key], list):
            dictionary[key].append(value)
        else:
            dictionary[key] = [dictionary[key], value]
        
        return dictionary

    def create_case(self, name, description, evidence):
        """Creates a case in Elastic Search under the efetch-cases index"""
        if not name:
            return
        case = {
                    '_index': 'efetch-cases',
                    '_type' : 'case',
                    '_id' : name,
                    '_source' : {
                        'name' : name,
                        'description' : description,
                        'evidence' : evidence
                    }
            }
        json = []
        json.append(case)
        helpers.bulk(self.elasticsearch, json)
        return

    def update_case(self, name, new_name, description, evidence):
        """Updates the current case"""
        #TODO switch to actual update
        self.delete_case(name)
        return self.create_case(new_name, description, evidence)

    def add_evidence_to_case(self, name, evidence, abort_on_error=True):
        """Adds a list of evidence to a given case by using the update_case method"""
        case = self.read_case(name)
        curr_evidence = case['_source']['evidence']
        description = case['_source']['description']
        return self.update_case(name, name, description, curr_evidence + evidence)

    def remove_evidence_from_case(self, name, evidence, abort_on_error=True):
        """Removes a list of evidence from a given case by using the update_case method"""
        case = self.read_case(name)
        curr_evidence = case['_source']['evidence']
        description = case['_source']['description']
        return self.update_case(name, name, description, [e for e in curr_evidence if e not in evidence])

    def get_evidence(self, name=None, abort_on_error=True):
        """Gets Efetch root evidence by name from Elastic Search"""
        if not name:
            indices = self.elasticsearch.indices.get_aliases().keys()
            evidence = []
            for index in sorted(indices):
                if str(index).startswith('efetch_evidence_'):
                    evidence.append(index[16:])
            return evidence
        else:
            return self.read_case(name)['_source']['evidence']

    def read_case(self, name=None, abort_on_error=True):
        """Gets Efetch case by name from Elastic Search"""
        if not name:
            return self.elasticsearch.search(index='efetch-cases', doc_type='case')
        return self.elasticsearch.get(index='efetch-cases', doc_type='case', id=name)

    def delete_case(self, name):
        """Deletes Efetch case by name from Elastic Search"""
        self.elasticsearch.delete(index='efetch-cases', doc_type='case', id=name)
        return

    def get_file(self, image_id, pid, abort_on_error=True):
        """Returns the file object for the given file in the database"""
        
        #Remove leading and trailing slashes
        if pid.endswith('/'):
            pid = pid[:-1]
        if str(pid).startswith('/'):
            pid = str(pid)[1:]

        #TODO CHECK IF IMAGE EXISTS
        #TODO Do not hide errors from elasticsearch
        curr_file = self.elasticsearch.search(index='efetch_evidence_' + image_id, doc_type='event',
                                              body={ 'query': {'bool': {'must': [{'term': {'pid': pid}},
                                                                       {'term': {'parser': 'efetch'}}]}}})
        if not curr_file['hits'] or not curr_file['hits']['hits'] or not curr_file['hits']['hits'][0]['_source']:
            logging.error("Could not find file. Image='" + image_id + "' pid='" + pid + "'")
            if abort_on_error:
                abort(404, "Could not find file in provided image.")
            else:
                return
    
        if len(curr_file['hits']['hits']) > 1:
            logging.warn("Found more than one file with pid " + pid)

        return curr_file['hits']['hits'][0]['_source']

    def create_index(self, index_name):
        """Create index in Elastic Search with the provided name"""
        self.elasticsearch.indices.create(index=index_name, ignore=400)

    def bulk(self, json):
        """Bulk adds json to Elastic Search"""
        helpers.bulk(self.elasticsearch, json)

    #TODO: Determine if abort on error should apply to conflicts
    def update(self, uuid, image_id, update, abort_on_error=True, repeat=1):
        """Updates evidence event in Elastic Search"""
        try:
            self.elasticsearch.update(index='efetch_evidence_' + image_id, doc_type='event', id=uuid, body={'doc': update})
        except ConflictError:
            if repeat > 0:
                logging.info('Failed to update "' + uuid + '" attempting again in 200ms')
                time.sleep(.200)
                self.update(uuid, image_id, update, abort_on_error, repeat - 1)
            logging.warn('Failed to update "' + uuid + '" due to conflict error!')


def efetch_root_node():
    """Returns the Elastic Search root node"""
    return {
                '_index': 'efetch-evidence',
                '_type' : 'event',
                '_id' : '/',
                '_source' : {
                    'pid' : '/',
                    'iid' : '/',
                    'image_id': '',
                    'image_path' : '',
                    'name' : 'Evidence',
                    'path' : '',
                    'ext' : '',
                    'dir' : '',
                    'meta_type' : 'Root',
                    'inode' : '',
                    'mtime' : '',
                    'atime' : '',
                    'ctime' : '',
                    'crtime' : '',
                    'file_size' : [0],
                    'uid' : '',
                    'gid' : '',
                    'driver' : "fa_dfvfs"
                }
        }


def evidence_template():
    """Returns the Elastic Search mapping for Evidence"""
    return {
        "template" : "efetch_evidence*",
        "settings" : {
            "number_of_shards" : 1
            },
        "mappings" : {
            "_default_" : {
                "_source" : { "enabled" : True },
                "properties" : {
                    "root" : {"type": "string", "index" : "not_analyzed"},
                    "pid" : {"type": "string", "index" : "not_analyzed"},
                    "iid" : {"type": "string", "index" : "not_analyzed"},
                    "image_id": {"type": "string", "index" : "not_analyzed"},
                    "image_path" : {"type": "string", "index" : "not_analyzed"},
                    "evd_type" : {"type": "string", "index" : "not_analyzed"},
                    "name" : {"type": "string", "index" : "not_analyzed"},
                    "path" : {"type": "string", "index" : "not_analyzed"},
                    "ext" : {"type": "string", "index" : "not_analyzed"},
                    "dir" : {"type": "string", "index" : "not_analyzed"},
                    "meta_type" : {"type": "string", "index" : "not_analyzed"},
                    "inode" : {"type": "string", "index" : "not_analyzed"},
                    "mtime" : {"type": "date", "format": "date_optional_time", "index" : "not_analyzed"},
                    "atime" : {"type": "date", "format": "date_optional_time", "index" : "not_analyzed"},
                    "ctime" : {"type": "date", "format": "date_optional_time", "index" : "not_analyzed"},
                    "crtime" : {"type": "date", "format": "date_optional_time","index" : "not_analyzed"},
                    "file_size" : {"type": "string", "index" : "not_analyzed"},
                    "uid" : {"type": "string", "index" : "not_analyzed"},
                    "gid" : {"type": "string", "index" : "not_analyzed"},
                    "driver" : {"type": "string", "index" : "not_analyzed"},
                    "source_short" : {"type": "string", "index" : "not_analyzed"},
                    "datetime" : {"type": "string", "index" : "not_analyzed"}
                    }
            }
        }
    }


def image_id_template():
    """Returns the Elastic Search mapping for Efetch Image IDs"""
    return {
        "template" : "efetch_image_ids",
        "settings" : {
            "number_of_shards" : 1
            },
        "mapping" : {
            "_default_" : {
                "_source" : { "enabled" : True },
                "properties" : {
                    "key" : {"type": "string", "index" : "not_analyzed"},
                    "value" : {"type": "string", "index" : "not_analyzed"},
                    }
                }
            }
        }


def case_template():
    """Returns the Elastic Search mapping for Efetch Cases"""
    return {
        "template" : "efetch-cases",
        "settings" : {
            "number_of_shards" : 1
            },
        "mapping" : {
            "_default_" : {
                "_source" : { "enabled" : True },
                "properties" : {
                    "name" : {"type": "string", "index" : "not_analyzed"},
                    "description" : {"type": "string", "index" : "analyzed"},
                    "evidence" : {
                        "properties" : {
                                "evidence" : {"type" : "string", "index" : "not_analyzed" }
                            }
                        }
                    }
                }
            }
        }


