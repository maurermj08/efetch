"""
A simple plugin that takes a file and returns the Strings in it
"""

from yapsy.IPlugin import IPlugin
import string
import re


class FaStrings(IPlugin):
    def __init__(self):
        self.display_name = 'Strings'
        self.popularity = 5
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
        return evidence['meta_type'] == 'File'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
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
