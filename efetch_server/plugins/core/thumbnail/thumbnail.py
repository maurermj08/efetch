"""
Returns a thumbnail or icon of the specified file
"""

from yapsy.IPlugin import IPlugin
from bottle import static_file
import os


class Thumbnail(IPlugin):
    def __init__(self):
        self.display_name = 'Thumbnail'
        self.popularity = 0
        self.cache = False
        self.fast = True
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
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns either an icon or thumbnail of the provided file"""
        # If it is folder just return the folder icon
        directory, file_name = os.path.split(helper.get_icon(evidence, False))
        return(static_file(file_name, directory, mimetype='image/png'))