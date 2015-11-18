#!/usr/bin/python
from bottle import abort
import logging
from elasticsearch import Elasticsearch, helpers
class DBUtil(object):
    """This class provides helper methods to be used in Efetch and its plugins"""
    global elasticsearch

    def __init__(self, es_url=None):
        global elasticsearch
        
        if es_url:
            elasticsearch = Elasticsearch([es_url])
        else:
            elasticsearch = Elasticsearch()
   
        #Elastic Search Setup
        elasticsearch.indices.create(index='efetch-config',ignore=400)
        elasticsearch.indices.create(index='efetch-log',ignore=400)
        elasticsearch.indices.create(index='efetch-cases',ignore=400)
        elasticsearch.indices.create(index='efetch-evidence',ignore=400)
        template = {
            "template" : "efetch_timeline*",
            "settings" : {
                "number_of_shards" : 1
                },
            "mappings" : {
                "_default_" : {
                    "_source" : { "enabled" : True },
                    "properties" : {
                        "id" : {"type": "string", "index" : "not_analyzed"},
                        "pid" : {"type": "string", "index" : "not_analyzed"},
                        "iid" : {"type": "string", "index" : "not_analyzed"},
                        "image_id": {"type": "string", "index" : "not_analyzed"},
                        "offset" : {"type": "string", "index" : "not_analyzed"},
                        "image_path" : {"type": "string", "index" : "not_analyzed"},
                        "name" : {"type": "string", "index" : "not_analyzed"},
                        "path" : {"type": "string", "index" : "not_analyzed"},
                        "ext" : {"type": "string", "index" : "not_analyzed"},
                        "dir" : {"type": "string", "index" : "not_analyzed"},
                        "file_type" : {"type": "string", "index" : "not_analyzed"},
                        "inode" : {"type": "string", "index" : "not_analyzed"},
                        "mod" : {"type": "date", "format": "epoch_second", "index" : "not_analyzed"},
                        "acc" : {"type": "date", "format": "epoch_second", "index" : "not_analyzed"},
                        "chg" : {"type": "date", "format": "epoch_second", "index" : "not_analyzed"},
                        "cre" : {"type": "date", "format": "epoch_second", "index" : "not_analyzed"},
                        "size" : {"type": "string", "index" : "not_analyzed"},
                        "uid" : {"type": "string", "index" : "not_analyzed"},
                        "gid" : {"type": "string", "index" : "not_analyzed"},
                        "thumbnail" : {"type": "string", "index" : "not_analyzed"},
                        "analyze" : {"type": "string", "index" : "not_analyzed"},
                        "driver" : {"type": "string", "index" : "not_analyzed"}
                        }
                }
            }
            }
        elasticsearch.indices.put_template(name="efetch_timeline", body=template)

    def get_file(self, image_id, offset, path, abort_on_error=True):
        """Returns the file object for the given file in the database"""
        if path.endswith('/'):
            path = path[:-1]

        #TODO CHECK IF IMAGE EXISTS
        #Check if image and offset are in database
        #    logging.error("Could not find image with provided id and offset " + image_id + "/" + offset)
        #    if abort_on_error:
        #        abort(400, "No image with id " + image_id + " and offset " + offset)
        #    else:
        #        return

        #TODO Do not hide errors from elasticsearch
        curr_file =  elasticsearch.get(index='efetch_timeline_' + image_id, doc_type='event', id=image_id + '/' + offset + '/' + path_or_inode)
        if not curr_file['_source']:
            logging.error("Could not find file. Image='" + image_id + "' Offset='" + offset + "' Type='" + input_type + "' Path or Inode='" + path_or_inode + "'")
            if abort_on_error:
                abort(404, "Could not find file in provided image.")
            else:
                return
        
        return curr_file['_source']
   
    #TODO add error checking
    def list_dir(self, directory):
        """Returns the list of files and folders within a directory"""
        result = elasticsearch.search(index='eftech_timeline_' + directory['image_id'], body={"query": { "term" : { "dir" : directory['name'] } } })
        return result['hits']['hits']

    def create_index(self, index_name):
        elasticsearch.indices.create(index=index_name, ignore=400)

    def bulk(self, json):
        helpers.bulk(elasticsearch, json)
