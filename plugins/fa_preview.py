"""
A simple plugin that takes a file and returns the Strings in it
"""

from yapsy.IPlugin import IPlugin
from bottle import static_file
import os

class FaPreview(IPlugin):

    
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
        return "Preview"

    def check(self, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        allowed = ['image/jpeg', 'image/png', 'image/gif', 'text/plain', 'text/html', 'application/pdf']
        print mimetype
        if str(mimetype).lower() in allowed:
            return True
        else:
            return False

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return mimetype

    def get(self, input_file, path_on_disk, mimetype, size):
        """Returns the result of this plugin to be displayed in a browser"""
        return static_file(os.path.basename(path_on_disk), root=os.path.dirname(path_on_disk))
