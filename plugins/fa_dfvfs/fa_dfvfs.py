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
        offset = request.query['offset']
        path = request.query['path']
        image_id = request.query['image_id']
        self.add_image(image_id, offset, path, helper.db_util, address, port)
        return '<xmp style="white-space: pre-wrap;">Done</xmp>'

    def add_image(self, image_id, offset, image_path, db_util, address, port):
        """Creates a file listing of the partition at the provided image and offset in the database"""
        if not str(image_path).startswith("/"):
            image_path = "/" + image_path

        if not os.path.isfile(image_path):
            logging.error("Could not find file at path '" + str(image_path) + "'")
            abort(400, "Could not find file at specified path '" + str(image_path) + "'")

        logging.info("Adding " + image_id + " to Elastic Search using dfVFS driver")

        #try:
        dfvfs_util = DfvfsUtil(image_path)
        index_name = 'efetch_timeline_' + image_id
        db_util.create_index(index_name)
        root = {
                    '_index': index_name,
                    '_type' : 'event',
                    '_id' : image_id + '/' + offset + '/',
                    '_source' : {
                        'id' : image_id + "/" + offset,
                        'pid' : image_id + '/' + offset + '/',
                        'iid' : image_id + '/' + offset + '/',
                        'image_id': image_id,
                        'offset' : offset,
                        'image_path' : image_path,
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
                        'thumbnail' : "http://" + address + ":" + port + "/plguins/fa_thumbnail/" + image_id + "/" + offset + '/',
                        'analyze' : "http://" + address + ":" + port + "/plugins/fa_analyze/" + image_id + "/" + offset + '/',
                        'driver' : "fa_tsk"
                    }
            }

        json = dfvfs_util.GetJson(image_id, offset, image_path, address, port)
        json.append(root)
        db_util.bulk(json)

    def icat(self, curr_file, output_file_path):
        """Returns the specified file using image file, meta or inode address, and outputfile"""
        dfvfs_util = DfvfsUtil(curr_file['image_path'])
        dfvfs_util.Icat(curr_file['path'], output_file_path)
