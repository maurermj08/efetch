#!/usr/bin/python
from bottle import abort
import logging
import sys
from elasticsearch import Elasticsearch, helpers
class DBUtil(object):
    """This class provides helper methods to be used in Efetch and its plugins"""
    elasticsearch = None

    def __init__(self, es_url=None):
        if es_url:
            self.elasticsearch = Elasticsearch([es_url])
        else:
            self.elasticsearch = Elasticsearch()
   
        #Elastic Search Setup
        self.elasticsearch.indices.create(index='efetch-config',ignore=400)
        self.elasticsearch.indices.create(index='efetch-log',ignore=400)
        self.elasticsearch.indices.create(index='efetch-cases',ignore=400)
        self.elasticsearch.indices.create(index='efetch-evidence',ignore=400)
        case_template = {
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
        self.elasticsearch.indices.put_template(name="efetch-case", body=case_template)

        template = {
            "template" : "efetch-evidence*",
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
                        "mtime" : {"type": "string", "index" : "not_analyzed"},
                        "atime" : {"type": "string", "index" : "not_analyzed"},
                        "ctime" : {"type": "string", "index" : "not_analyzed"},
                        "crtime" : {"type": "string","index" : "not_analyzed"},
                        "file_size" : {"type": "string", "index" : "not_analyzed"},
                        "uid" : {"type": "string", "index" : "not_analyzed"},
                        "gid" : {"type": "string", "index" : "not_analyzed"},
                        "driver" : {"type": "string", "index" : "not_analyzed"}
                        }
                }
            }
            }
        self.elasticsearch.indices.put_template(name="efetch-evidence", body=template)

    def get_file_from_ppid(self, ppid, abort_on_error=True):
        """Returns the file object for the given file in the database"""
        return self.get_file(ppid.split('/')[0], ppid, abort_on_error)

    def create_case(self, name, description, evidence):
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

    #TODO switch to actual update
    def update_case(self, name, new_name, description, evidence):
        """Updates the current case"""
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
        if not name:
            indices = self.elasticsearch.indices.get_aliases().keys()
            evidence = []
            for index in sorted(indices):
                if str(index).startswith('efetch-evidence_'):
                    evidence.append(index[16:])
            return evidence
        else:
            return self.read_case(name)['_source']['evidence']

    def read_case(self, name=None, abort_on_error=True):
        if not name:
            return self.elasticsearch.search(index='efetch-cases', doc_type='case')
        return self.elasticsearch.get(index='efetch-cases', doc_type='case', id=name)

    def delete_case(self, name):
        self.elasticsearch.delete(index='efetch-cases', doc_type='case', id=name)
        return

    def get_file(self, image_id, evd_id, abort_on_error=True):
        """Returns the file object for the given file in the database"""
        
        #Remove leading and trailing slashes
        if evd_id.endswith('/'):
            evd_id = evd_id[:-1]
        if str(evd_id).startswith('/'):
            evd_id = str(evd_id)[1:]

        #TODO CHECK IF IMAGE EXISTS
        #Check if image and offset are in database
        #    logging.error("Could not find image with provided id and offset " + image_id + "/" + offset)
        #    if abort_on_error:
        #        abort(400, "No image with id " + image_id + " and offset " + offset)
        #    else:
        #        return

        #TODO Do not hide errors from elasticsearch
        #curr_file =  elasticsearch.get(index='efetch-evidence_' + image_id, doc_type='event', id=evd_id)
        curr_file = self.elasticsearch.search(index='efetch-evidence_' + image_id, doc_type='event', body={"query": {"match": {"pid": evd_id}}})
        if not curr_file['hits'] or not curr_file['hits']['hits'] or not curr_file['hits']['hits'][0]['_source']:
            logging.error("Could not find file. Image='" + image_id + "' Type='" + input_type + "' _id='" + evd_id + "'")
            if abort_on_error:
                abort(404, "Could not find file in provided image.")
            else:
                return
    
        if len(curr_file['hits']['hits']) > 1:
            logging.warn("Found more than one file with pid " + evd_id)

        return curr_file['hits']['hits'][0]['_source']

    #TODO add error checking
    def list_dir(self, directory):
        """Returns the list of files and folders within a directory"""
        query_dir = directory['pid'] + '/'
       
        query = {
                "query": { 
                    "match" : 
                    { 
                        "dir" : query_dir
                        } 
                    },
                "size" : 10000
                }
        result = self.elasticsearch.search(index='efetch-evidence_' + directory['image_id'], body=query)
        logging.debug("Listed directory " + directory['name'] + " and found " + str(len(result['hits']['hits'])) + " entries")
        return result['hits']['hits']

    def create_index(self, index_name):
        self.elasticsearch.indices.create(index=index_name, ignore=400)

    def bulk(self, json):
        helpers.bulk(self.elasticsearch, json)

    def update_by_ppid(self, ppid, update, abort_on_error=True):
        """Returns the file object for the given file in the database"""
        ppid_split = str(ppid).split('/')
        image_id = ppid_split[0]
        path = '/'.join(ppid_split[1:])
        print("path: " + path + ", image_id: " + image_id)
        self.update(ppid, image_id, update, abort_on_error)

    def update(self, ppid, image_id, update, abort_on_error=True):
        #try:
        self.elasticsearch.update(index='efetch-evidence_' + image_id, doc_type='event', id=ppid, body={'doc': update})
        #except:
        #    if abort_on_error:
        #        abort(404, "Could not update document with id: " +image_id + '/' + path)
        #    else:
        #        return
