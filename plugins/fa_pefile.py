"""
Displays Info About Windows Portable Executables
"""

from yapsy.IPlugin import IPlugin

import pefile


class FaPefile(IPlugin):
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
        return "PE File"

    def check(self, curr_file, path_on_disk, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        allowed = ['application/x-dosexec']
        return str(mimetype).lower() in allowed

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 5

    def get(self, curr_file, database, path_on_disk, mimetype, size, address, port, request_query):
        """Returns the result of this plugin to be displayed in a browser"""
        pe = pefile.PE(path_on_disk)
        return '<xmp style="white-space: pre-wrap;">\n' + pe.dump_info() + "</xmp>"
