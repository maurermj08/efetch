"""
Simple file browser
"""

from yapsy.IPlugin import IPlugin
import ast
import os
import time

class FaFileBrowser(IPlugin):

    def __init__(self):
        self._display_name = 'FileBrowser'
        self._popularity = 0
        self._parent = True
        self._cache = False
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns a formatted directory listing for the given path"""
        return helper.plugin_manager.getPluginByName('fa_browser').plugin_object.get(evidence,
                helper, path_on_disk, request, children, True, False, 'fa_filebrowser')
