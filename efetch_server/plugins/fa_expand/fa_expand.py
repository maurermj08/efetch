"""
Force expand of evidence
"""

from yapsy.IPlugin import IPlugin
import logging


class Directory(IPlugin):

    def __init__(self):
        self.display_name = 'Expand'
        self.popularity = 9
        self.category = 'misc'
        self.cache = False
        self.fast = False
        self.action = False
        self.icon = 'fa-hdd-o'

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
        base_pathspec = helper.pathspec_helper.list_base_pathspecs(evidence)
        pathspec = base_pathspec[0]['pathspec']
        return helper.plugin_manager.run_plugin('directory', pathspec, helper, request)
