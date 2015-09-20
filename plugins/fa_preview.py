"""
This plugin returns common files that can be opened in a browser i.e. images and PDF documents
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

    def check(self, curr_file, path_on_disk, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        allowed = ['image/jpeg', 'image/png', 'image/gif', 'text/plain', 'text/html', 'application/pdf']
        return str(mimetype).lower() in allowed and curr_file['file_type'] != 'directory'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return mimetype

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 8

    def get(self, curr_file, database, path_on_disk, mimetype, size, address, port, request_query):
        """Returns the result of this plugin to be displayed in a browser"""
        return static_file(os.path.basename(path_on_disk), root=os.path.dirname(path_on_disk))
