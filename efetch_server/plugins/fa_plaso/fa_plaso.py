"""
Creates a timeline using Log2timeline
"""

from yapsy.IPlugin import IPlugin



class FaPlaso(IPlugin):

    def __init__(self):
        self.display_name = 'Create Timeline'
        self.popularity = 5
        self.cache = False
        self.fast = False
        self.action = False
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        return False

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        #https://github.com/log2timeline/plaso/blob/508eb361b7f484d083e9069bba8a9c6b5cce1c03/plaso/multi_processing/task_engine.py

        # Need to call ProcessSources

        return '<xmp style="white-space: pre-wrap;">TODO</xmp>'
