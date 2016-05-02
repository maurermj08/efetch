"""
This plugin returns common files that can be opened in a browser i.e. images and PDF documents
"""

from yapsy.IPlugin import IPlugin
from bottle import static_file
import os


class FaPreview(IPlugin):
    def __init__(self):
        self.display_name = 'Preview'
        self.popularity = 8
        self.parent = False
        self.cache = True
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        allowed_mimetype = ['application/xml', 'application/pdf']
        allowed_prefix = ['image', 'text', 'video', 'audio']
        return (str(evidence['mimetype'].split('/')[0]).lower() in allowed_prefix
                or evidence['mimetype'] in allowed_mimetype ) and evidence['meta_type'] != 'Directory'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return evidence['mimetype']

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        return static_file(os.path.basename(path_on_disk), root=os.path.dirname(path_on_disk))
