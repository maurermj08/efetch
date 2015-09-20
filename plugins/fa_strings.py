"""
A simple plugin that takes a file and returns the Strings in it
"""

from yapsy.IPlugin import IPlugin
import string
import codecs

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
        return size < maxsize and curr_file['file_type'] != 'directory'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 5

    def get(self, curr_file, database, path_on_disk, mimetype, size, address, port, request_query):
        """Returns the result of this plugin to be displayed in a browser"""
        input_file = open(path_on_disk, 'rb')
        strings = list(self.get_file_strings(input_file))
        input_file = codecs.open(path_on_disk, 'rb', "utf-8")
        strings.extend(list(self.get_file_strings(input_file)))
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
