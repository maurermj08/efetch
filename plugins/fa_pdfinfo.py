"""
Prints the metadata of a PDF file
"""

from yapsy.IPlugin import IPlugin
import os

class FaPdfinfo(IPlugin):

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
        return "PDF Info"

    def check(self, curr_file, path_on_disk, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        allowed = [ 'application/pdf' ]
        return curr_file['file_type'] == 'regular' and str(mimetype).lower() in allowed

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 5
    
    def cache(self):
        """Returns if caching is required"""
        return True

    def get(self, curr_file, helper, path_on_disk, mimetype, size, address, port, request_query):
        """Returns the result of this plugin to be displayed in a browser"""
        process = os.popen('pdfinfo ' + path_on_disk)
        pdfinfo = process.read()
        process.close()
        return '<xmp style="white-space: pre-wrap;">' + pdfinfo + '</xmp>'
