"""
Parses evidence into database using dfVFS
"""

from yapsy.IPlugin import IPlugin
from dfvfs_util import DfvfsUtil
import pytsk3
import os
import logging
from bottle import abort

class FaDfvfs(IPlugin):

    utils = {}

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
        return "dfVFS"

    def check(self, curr_file, path_on_disk, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 0

    def parent(self):
        """Returns if the plugin accepts other plugins (True) or only files (False)"""
        return False
    
    def cache(self):
        """Returns if caching is required"""
        return False

    def get(self, curr_file, helper, path_on_disk, mimetype, size, address, port, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        path = request.query['path']
        image_id = request.query['image_id']
        self.add_image(image_id, path, helper.db_util, [])
        return '<xmp style="white-space: pre-wrap;">Done</xmp>'

    def add_image(self, image_id, image_path, db_util, settings):
        """Creates a file listing of the partition at the provided image in the database"""
        if not str(image_path).startswith("/"):
            image_path = "/" + image_path

        if not os.path.isfile(image_path):
            logging.error("Could not find file at path '" + str(image_path) + "'")
            abort(400, "Could not find file at specified path '" + str(image_path) + "'")

        logging.info("Adding " + image_id + " to Elastic Search using dfVFS driver")

        #try:
        dfvfs_util = DfvfsUtil(image_path, settings, False)
        if dfvfs_util.initialized < 1:
            return dfvfs_util.display
        
        index_name = 'efetch-evidence_' + image_id
        db_util.create_index(index_name)
        root = {
                    '_index': index_name,
                    '_type' : 'event',
                    '_id' : image_id + '/',
                    '_source' : {
                        'id' : image_id,
                        'pid' : image_id + '/',
                        'iid' : image_id + '/',
                        'image_id': image_id,
                        'image_path' : image_path,
                        'evd_type' : 'root',
                        'name' : '/',
                        'path' : '/',
                        'ext' : '',
                        'dir' : '',
                        'file_type' : 'directory',
                        'inode' : '',
                        'mod' : 0,
                        'acc' : 0,
                        'chg' : 0,
                        'cre' : 0,
                        'size' : '',
                        'uid' : '',
                        'gid' : '',
                        'driver' : "fa_dfvfs"
                    }
            }

        json = []
        json.append(root)
        
        curr_id = image_id + '/'
        curr_path = '/'
        settings.append('ROOT')

        for setting in settings:
            curr_id += setting
            curr_path += setting + '/'
            json.append({
                    '_index': index_name,
                    '_type' : 'event',
                    '_id' : curr_id + '/',
                    '_source' : {
                        'id' : curr_id,
                        'pid' : curr_id + '/',
                        'iid' : curr_id + '/',
                        'image_id': image_id,
                        'image_path' : image_path,
                        'evd_type' : 'part',
                        'name' : setting + '/',
                        'path' : curr_path,
                        'ext' : '',
                        'dir' : '',
                        'file_type' : 'directory',
                        'inode' : '',
                        'mod' : 0,
                        'acc' : 0,
                        'chg' : 0,
                        'cre' : 0,
                        'size' : '',
                        'uid' : '',
                        'gid' : '',
                        'driver' : "fa_dfvfs"
                    }
            })

        json += dfvfs_util.GetJson(image_id, curr_id, image_path)
        db_util.bulk(json)

    def icat(self, curr_file, output_file_path):
        """Returns the specified file using image file, meta or inode address, and outputfile"""
        if not curr_file['id'] in self.utils:
            settings = []
            curr_id = curr_file['id'].split('/')[1:]
            while curr_id[0] != 'ROOT':
                settings.append(curr_id.pop(0))
            settings.append('none')
            self.utils[curr_file['id']] = DfvfsUtil(curr_file['image_path'], settings, False)
        
        dfvfs_util = self.utils[curr_file['id']]
        
        if dfvfs_util.initialized > 0:
            dfvfs_util.Icat(curr_file['path'], output_file_path)
        else:
            logging.warn("Unable to icat file %s because no proper dfVFS settings", curr_file['pid'])
