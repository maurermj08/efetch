"""
Get the hash of a file
"""

from yapsy.IPlugin import IPlugin
import hashlib
import datetime

class FaHash(IPlugin):

    def __init__(self):
        self._display_name = 'File Hasher'
        self._popularity = 5
        self._parent = False 
        self._cache = True
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        return evidence['meta_type'] == 'File'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        block_size = 65536
        hashers = { 'md5': hashlib.md5(), 'sha1': hashlib.sha1(), 'sha224': hashlib.sha224(), 'sha256': hashlib.sha256(), 'sha384': hashlib.sha384(), 'sha512': hashlib.sha512() }
        try:
            hash_type = request.query['type'] 
            if hash_type not in hashers.keys():
                hash_type = 'md5'
        except:
            hash_type = 'md5'
        hasher = hashers[hash_type]

        with open(path_on_disk, 'rb') as fh:
            data = fh.read(block_size) 
            while data:
               hasher.update(data)
               data = fh.read(block_size) 
            fh.close()
            hash_time = datetime.datetime.now()
            hash_result = hasher.hexdigest()
            update = {hash_type: hash_time, hash_type + "_digest": hash_result}
            file_id = evidence['pid']
            helper.db_util.update_by_ppid(file_id, update)
            return '<xmp style="white-space: pre-wrap;">Done</xmp>'
        return '<xmp style="white-space: pre-wrap;">Error</xmp>'
                 
