"""
Runs a single plugin against multiple path specs from an Elasticsearch query
"""

from yapsy.IPlugin import IPlugin
import logging
from bottle import abort


class FaAction(IPlugin):

    def __init__(self):
        self.display_name = 'Action'
        self.popularity = 0
        self.cache = False
        self.fast = True
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
        index = helper.get_request_value(request, 'index', False)
        theme = helper.get_theme(request)

        # method = helper.get_request_value(request, 'method')
        # plugin = helper.get_request_value(request, 'plugin', False)
        # size = helper.get_request_value(request, 'size', 10000)
        # sort = helper.get_request_value(request, 'sort', False)
        # order = helper.get_request_value(request, 'order', 'asc')

        if not index:
            abort(400, 'Action plugin requires an index, but none found')

        return '<xmp style="white-space: pre-wrap;">Done</xmp>'
