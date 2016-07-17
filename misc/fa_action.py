"""
Runs a single plugin against multiple path specs from an Elasticsearch query
"""

from yapsy.IPlugin import IPlugin



class FaAction(IPlugin):

    def __init__(self):
        self.display_name = 'Action'
        self.popularity = 0
        self.cache = False
        self.fast = False
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        return '<xmp style="white-space: pre-wrap;">TODO</xmp>'
