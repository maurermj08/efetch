"""
Get the hash of a file
"""

from yapsy.IPlugin import IPlugin
import hashlib
import datetime

class FaHash(IPlugin):

    def __init__(self):
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def display_name(self):
        """Returns the name displayed in the webview"""
        return "File Hasher"

    def check(self, curr_file, path_on_disk, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        return curr_file['file_type'] == 'regular'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 5

    def parent(self):
        """Returns if the plugin accepts other plugins (True) or only files (False)"""
        return False

    def cache(self):
        """Returns if caching is required"""
        return True

    def get(self, curr_file, helper, path_on_disk, mimetype, size, address, port, request, children):
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
            file_id = curr_file['pid']
            helper.db_util.update_by_ppid(file_id, update)
            return '<xmp style="white-space: pre-wrap;">Done</xmp>'
        return '<xmp style="white-space: pre-wrap;">Error</xmp>'
                 
