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

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        allowed = ['image/jpeg', 'image/png', 'image/gif', 'text/plain', 'text/html', 'application/pdf']
        return str(evidence['mimetype']).lower() in allowed and evidence['meta_type'] != 'Directory'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return evidence['mimetype']

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 8

    def parent(self):
        """Returns if the plugin accepts other plugins (True) or only files (False)"""
        return False

    def cache(self):
        """Returns if caching is required"""
        return True

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        return static_file(os.path.basename(path_on_disk), root=os.path.dirname(path_on_disk))
