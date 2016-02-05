"""
A simple plugin that takes a file and returns the Strings in it
"""

from yapsy.IPlugin import IPlugin
import string
import re

class FaStrings(IPlugin):

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
        return "Strings"

    def check(self, curr_file, path_on_disk, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        maxsize = 100000000 
        return size < maxsize and curr_file['meta_type'] != 'Directory'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 5

    def parent(self):
        """Returns if the plugin accepts other plugins (True) or only files (False)"""
        return False

    def cache(self):
        """Returns if caching is required"""
        return True

    def get(self, curr_file, helper, path_on_disk, mimetype, size, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        input_file = open(path_on_disk, 'rb')
        strings = list(self.get_file_strings(input_file))
        input_file.close()
        return '<xmp style="white-space: pre-wrap;">' + "\n".join(strings) + '</xmp>'

    def get_file_strings(self, input_file, min=4):
        chars = r"A-Za-z0-9/\-:.,_$%'()[\]<> "
        regexp = '[%s]{%d,}' % (chars, min)
        pattern = re.compile(regexp)
        data = input_file.read()
        return pattern.findall(data)
