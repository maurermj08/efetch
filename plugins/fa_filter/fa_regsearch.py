"""
A parent plugin that adds a filter to its child plugins
"""

import json
import logging
import os
import uuid
from bottle import abort
from yapsy.IPlugin import IPlugin


class FaRegSearch(IPlugin):
    def __init__(self):
        self.display_name = 'Regex Search'
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
        """Checks if the file is compatable with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children):
        """Gets the filter bar"""
        return helper.plugin_manager.getPluginByName('fa_filter').plugin_object.get(evidence,
                                                                                     helper, path_on_disk, request,
                                                                                     children, 'regexp',
                                                                                     'fa_regsearch', self.display_name)
