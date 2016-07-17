"""
Get the hash of a file
"""

from yapsy.IPlugin import IPlugin
import hashlib
import datetime
import logging
from bottle import abort


class FaHash(IPlugin):
    def __init__(self):
        self.display_name = 'File Hasher'
        self.popularity = 0
        self.parent = False
        self.cache = True
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        return evidence['meta_type'] == 'File'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        block_size = 65536
        hashers = {'md5': hashlib.md5(), 'sha1': hashlib.sha1(), 'sha224': hashlib.sha224(), 'sha256': hashlib.sha256(),
                   'sha384': hashlib.sha384(), 'sha512': hashlib.sha512()}

        index = helper.get_request_value(request, 'index', False)
        if not index:
            abort(400, 'Hash plugin requires an index, but none found')

        id_value = helper.get_request_value(request, 'id', False)
        if not id_value and '_id' not in evidence:
            abort(400, 'ID required to Star Elasticsearch doc')
        elif not id_value:
            id_value = evidence['_id']

        if 'doc_type' not in evidence:
            event = helper.db_util.query_id(id_value, index)
            if not event:
                logging.warn('Toggle Start failed to find event with ID "' + id_value + '"')
                abort(400, 'Failed to find event wit ID "' + id_value + '"')
            doc_type = event['_type']
        else:
            doc_type = evidence['doc_type']

        try:
            hash_type = request.query['type']
            if hash_type not in hashers.keys():
                hash_type = 'md5'
        except:
            hash_type = 'md5'
        hasher = hashers[hash_type]

        if hash_type + '_digest' not in evidence:
            # try:
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
            # except:
            #     logging.warn('Failed to hash file')
            #     return '<xmp style="white-space: pre-wrap;">Error</xmp>'
        else:
            hash_result = evidence[hash_type + '_digest']

        return '<xmp style="white-space: pre-wrap;">' + hash_type + ': ' + hash_result + '</xmp>'

