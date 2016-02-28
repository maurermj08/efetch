"""
Returns a thumbnail or icon of the specified file
"""

from yapsy.IPlugin import IPlugin
from bottle import static_file
import os

class FaThumbnail(IPlugin):

    def __init__(self):
        self._display_name = 'Thumbnail'
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
        """Returns either an icon or thumbnail of the provided file"""
        #If it is folder just return the folder icon
        if evidence['meta_type'] == 'Directory' or str(evidence['name']).strip() == "." or str(evidence['name']).strip() == "..":
            return static_file("_folder.png", root=helper.icon_dir, mimetype='image/png')

        #Uses extension to determine if it should create a thumbnail
        #assumed_mimetype = helper.guess_mimetype(str(evidence['ext']).lower())

        #If the file is an image create a thumbnail
        if evidence['mimetype'].startswith('image'):
            #Cache file
            file_cache_path = helper.cache_file(evidence)
            thumbnail_cache_path = helper.output_dir + 'thumbnails/' + evidence['iid'] + '/' + evidence['name']
            thumbnail_cache_dir = helper.output_dir + 'thumbnails/' + evidence['iid'] + '/'
            #TODO: If this is always a jpeg just state it, should save some time
            thumbnail_mimetype = helper.get_mimetype(thumbnail_cache_path)

            if os.path.isfile(thumbnail_cache_path):
                return static_file(evidence['name'], root=thumbnail_cache_dir, mimetype=thumbnail_mimetype)
            else:
                return static_file('_missing.png', root=helper.icon_dir, mimetype='image/png')
        #If file is not an image return the icon associated with the files extension
        else:
            if not os.path.isfile(helper.icon_dir + str(evidence['ext']).lower() + ".png"):
                return static_file("_blank.png", root=helper.icon_dir, mimetype='image/png')
            else:
                return static_file(evidence['ext'].lower() + ".png", root=helper.icon_dir, mimetype='image/png')
