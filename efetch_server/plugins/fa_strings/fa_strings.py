"""
A simple plugin that takes a file and returns the Strings in it
"""

from yapsy.IPlugin import IPlugin


class FaStrings(IPlugin):
    def __init__(self):
        self.display_name = 'Strings'
        self.popularity = 5
        self.cache = False
        self.fast = False
        self.action = False
        self.icon = 'fa-file-text-o'
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
        return '<xmp style="white-space: pre-wrap;">' + \
               "\n".join(helper.pathspec_helper.get_file_strings(evidence['pathspec'])) + '</xmp>'