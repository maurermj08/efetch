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
    
    def cache(self):
        """Returns if caching is required"""
        return False

    def get(self, curr_file, helper, path_on_disk, mimetype, size, address, port, request_query):
        """Returns the result of this plugin to be displayed in a browser"""
        offset = request_query['offset']
        path = request_query['path']
        image_id = request_query['image_id']
        self.add_image(image_id, offset, path, helper.db_util, address, port)
        return '<xmp style="white-space: pre-wrap;">Done</xmp>'

    def add_image(self, image_id, offset, image_path, db_util, address, port):
        """Creates a file listing of the partition at the provided image and offset in the database"""
        if not str(image_path).startswith("/"):
            image_path = "/" + image_path

        if not os.path.isfile(image_path):
            logging.error("Could not find file at path '" + str(image_path) + "'")
            abort(400, "Could not find file at specified path '" + str(image_path) + "'")

        logging.info("Adding image to databse")

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

        json = self.load_database(dfvfs_util, image_id, offset, image_path, index_name, "/", address, port)
        json.append(root)
        db_util.bulk(json)

    def icat(self, curr_file, output_file_path):
        """Returns the specified file using image file, meta or inode address, and outputfile"""
        dfvfs_util = DfvfsUtil(curr_file['image_path'])
        dfvfs_util.Icat(curr_file['path'], output_file_path)

    def load_database(self, dfvfs_util, image_id, offset, image_path, index_name, directory, address, port):
        json = []
        if directory == "/":
            dir_list = dfvfs_util.ListRoot()
        else:
            dir_list = dfvfs_util.ListDir(directory)
        print("DIR:  " + directory)

        for name in dir_list:
            my_file = dfvfs_util.GetFile(directory + name)

            directory_entry = my_file._tsk_file
            if directory_entry.info.meta == None:
                file_type = ''
                inode = ''
                mod = ''
                acc = ''
                chg = ''
                cre = ''
                size = ''
                uid = ''
                gid = ''
            else:
                file_type = directory_entry.info.meta.type
                inode = str(directory_entry.info.meta.addr)
                mod = str(directory_entry.info.meta.mtime)
                acc = str(directory_entry.info.meta.atime)
                chg = str(directory_entry.info.meta.ctime)
                cre = str(directory_entry.info.meta.crtime)
                size = str(directory_entry.info.meta.size)
                uid = str(directory_entry.info.meta.uid)
                gid = str(directory_entry.info.meta.gid)

            dir_ref = image_id + "/" + offset + directory + name
            inode_ref = image_id + "/" + offset + "/" + inode
            ext = os.path.splitext(name)[1][1:] or ""
    
            if file_type == None:
                file_type_str = 'None'
            elif file_type == pytsk3.TSK_FS_META_TYPE_REG:
                file_type_str = 'regular'
            elif file_type == pytsk3.TSK_FS_META_TYPE_DIR:
                file_type_str = 'directory'
            elif file_type == pytsk3.TSK_FS_META_TYPE_LNK:
                file_type_str = 'link'
            else:
                file_type_str = str(file_type)

            modtime = long(mod) if mod else 0
            acctime = long(acc) if acc else 0
            chgtime = long(chg) if chg else 0
            cretime = long(cre) if cre else 0

            meta_event = {
                    '_index': index_name,
                    '_type' : 'event',
                    '_id' : dir_ref,
                    '_source' : {
                        'id' : image_id + "/" + offset,
                        'pid' : dir_ref,
                        'iid' : inode_ref,
                        'image_id': image_id,
                        'offset' : offset,
                        'image_path' : image_path,
                        'name' : name,
                        'path' : str(directory) + name,
                        'ext' : ext,
                        'dir' : directory,
                        'file_type' : file_type_str,
                        'inode' : inode,
                        'mod' : modtime,
                        'acc' : acctime,
                        'chg' : chgtime,
                        'cre' : cretime,
                        'size' : size,
                        'uid' : uid,
                        'gid' : gid,
                        'thumbnail' : "http://" + address + ":" + port + "/plugins/fa_thumbnail/" + image_id + "/" + offset + directory + name,
                        'analyze' : "http://" + address + ":" + port + "/plugins/fa_analyze/" + image_id + "/" + offset + directory + name,
                        'driver' : "fa_dfvfs"
                    }
            }

            json.append(meta_event)

            if file_type == pytsk3.TSK_FS_META_TYPE_DIR and name != "." and name != "..":
                try:
                    json.extend(self.load_database(dfvfs_util, image_id, offset, image_path, index_name, directory + name + "/", address, port))
                except Exception as error:
                    logging.warn("[WARNING] - Failed to parse directory " + directory + name + "/")
            elif file_type == pytsk3.TSK_FS_META_TYPE_REG:
                my_file.close()

        return json

