"""
Prints the metadata of a PDF file
"""

from yapsy.IPlugin import IPlugin
import os


class FaPdfinfo(IPlugin):
    def __init__(self):
        self.display_name = 'PDF Info'
        self.popularity = 5
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
        allowed = ['application/pdf']
        return evidence['meta_type'] == 'File' and str(evidence['mimetype']).lower() in allowed

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        process = os.popen('pdfinfo ' + path_on_disk)
        pdfinfo = process.read()
        process.close()
        return '<xmp style="white-space: pre-wrap;">' + pdfinfo + '</xmp>'
