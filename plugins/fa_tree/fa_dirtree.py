"""
Lazy loading directory browsing tree
"""

from yapsy.IPlugin import IPlugin
from bottle import abort
import os
import json


class FaFileTree(IPlugin):
    def __init__(self):
        self.display_name = 'Directory Tree'
        self.popularity = 0
        self.parent = True
        self.cache = False
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

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        return helper.plugin_manager.getPluginByName('fa_tree').plugin_object.get(evidence,
                                                                                  helper, path_on_disk, request,
                                                                                  children, False, True, 'fa_dirtree')
