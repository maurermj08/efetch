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
        self._display_name = 'dfVFS'
        self._popularity = 0
        self._parent = False
        self._cache = False
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children):
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
                        'meta_type' : 'Directory',
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
        settings.append('TSK')

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
                        'meta_type' : 'Directory',
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

    def icat(self, evidence, output_file_path):
        """Returns the specified file using image file, meta or inode address, and outputfile"""
        if not evidence['root'] in self.utils:
            settings = []
            curr_id = evidence['root'].split('/')[1:]
            while curr_id[0] != 'TSK':
                settings.append(curr_id.pop(0).lower())
            settings.append('none')
            self.utils[evidence['root']] = DfvfsUtil(evidence['image_path'], settings, False)
        
        dfvfs_util = self.utils[evidence['root']]
        
        if dfvfs_util.initialized > 0:
            dfvfs_util.Icat(evidence['path'], output_file_path)
        else:
            logging.warn("Unable to icat file %s because no proper dfVFS settings", evidence['pid'])
