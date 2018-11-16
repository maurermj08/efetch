"""
Get the hash of a file
"""

from yapsy.IPlugin import IPlugin
import hashlib
import datetime
import logging
import os


# TODO THIS WHOLE PLUGIN NEEDS REWRITTEN
class FaHash(IPlugin):
    def __init__(self):
        self.display_name = 'File Hasher'
        self.category = 'data'
        self.popularity = 0
        self.cache = True
        self.fast = False
        self.action = True
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        return path_on_disk and os.path.isfile(path_on_disk) and evidence['meta_type'] == 'File'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        block_size = 65536
        hashers = {'md5': hashlib.md5(), 'sha1': hashlib.sha1(), 'sha224': hashlib.sha224(), 'sha256': hashlib.sha256(),
                   'sha384': hashlib.sha384(), 'sha512': hashlib.sha512()}

        index = helper.get_request_value(request, 'index', False, raise_key_error=True)

        id_value = helper.get_request_value(request, 'id', False)
        if not id_value and '_id' not in evidence:
            logging.error('ID required to hash Elasticsearch doc')
            raise ValueError('Valid ID required to hash Elasticsearch doc')
        elif not id_value:
            id_value = evidence['_id']

        if 'doc_type' not in evidence:
            event = helper.db_util.query_id(id_value, index)
            if not event:
                logging.error('Failed to find event in Elasticsearch')
                raise KeyError('Event not found in query')
            doc_type = event['_type']
        else:
            doc_type = evidence['doc_type']

        try:
            hash_type = helper.get_request_value(request, 'type')
            if hash_type not in hashers.keys():
                hash_type = 'md5'
        except:
            hash_type = 'md5'
        hasher = hashers[hash_type]

        if hash_type + '_digest' not in evidence:
            try:
                with open(path_on_disk, 'rb') as fh:
                    data = fh.read(block_size)
                    while data:
                        hasher.update(data)
                        data = fh.read(block_size)
                    fh.close()
                    hash_time = datetime.datetime.now()
                    hash_result = hasher.hexdigest()
                    update = {hash_type + '_time': hash_time, hash_type + "_digest": hash_result}
                    helper.db_util.update(id_value, index, update, doc_type=doc_type)
            except:
                logging.warn('Failed to hash file')
                return '<xmp style="white-space: pre-wrap;">Error</xmp>'
        else:
            hash_result = evidence[hash_type + '_digest']

        return '<xmp style="white-space: pre-wrap;">' + hash_type + ': ' + hash_result + '</xmp>'

