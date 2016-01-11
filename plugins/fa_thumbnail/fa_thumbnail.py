"""
Returns a thumbnail or icon of the specified file
"""

from yapsy.IPlugin import IPlugin
from bottle import static_file
import os

class FaThumbnail(IPlugin):

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
        return "Thumbnail"

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
        """Returns either an icon or thumbnail of the provided file"""
        #If it is folder just return the folder icon
        if curr_file['file_type'] == 'directory' or str(curr_file['name']).strip() == "." or str(curr_file['name']).strip() == "..":
            return static_file("_folder.png", root=helper.icon_dir, mimetype='image/png')

        #Uses extension to determine if it should create a thumbnail
        assumed_mimetype = helper.guess_mimetype(str(curr_file['ext']).lower())

        #If the file is an image create a thumbnail
        if assumed_mimetype.startswith('image'):
            #Cache file
            file_cache_path = helper.cache_file(curr_file)
            thumbnail_cache_path = helper.output_dir + 'thumbnails/' + curr_file['iid'] + '/' + curr_file['name']
            thumbnail_cache_dir = helper.output_dir + 'thumbnails/' + curr_file['iid'] + '/'
            #TODO: If this is always a jpeg just state it, should save some time
            thumbnail_mimetype = helper.get_mimetype(thumbnail_cache_path)

            if os.path.isfile(thumbnail_cache_path):
                return static_file(curr_file['name'], root=thumbnail_cache_dir, mimetype=thumbnail_mimetype)
            else:
                return static_file('_missing.png', root=helper.icon_dir, mimetype='image/png')
        #If file is not an image return the icon associated with the files extension
        else:
            if not os.path.isfile(helper.icon_dir + str(curr_file['ext']).lower() + ".png"):
                return static_file("_blank.png", root=helper.icon_dir, mimetype='image/png')
            else:
                return static_file(curr_file['ext'].lower() + ".png", root=helper.icon_dir, mimetype='image/png')
