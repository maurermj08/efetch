"""
A simple plugin that takes a file and returns the Strings in it
"""

from yapsy.IPlugin import IPlugin
import string

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

    def check(self, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        maxsize = 100000000 
        if (size < maxsize):
            return True
        else:
            return False

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, input_file, path_on_disk, mimetype, size):
        """Returns the result of this plugin to be displayed in a browser"""
        strings = list(self.get_file_strings(input_file))
        return '<xmp style="white-space: pre-wrap;">' + "\n".join(strings) + '</xmp>'

    def get_file_strings(self, input_file, min=4):
        result = ""
        for c in input_file.read():
            if c in string.printable:
                result += c
                continue
            if len(result) >= min:
                yield result
            result = ""
