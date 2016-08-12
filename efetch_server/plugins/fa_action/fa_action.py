"""
Runs a single plugin against multiple path specs from an Elasticsearch query
"""

from yapsy.IPlugin import IPlugin
import logging
import os
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

        if not index:
            abort(400, 'Action plugin requires an index, but none found')

        curr_dir = os.path.dirname(os.path.realpath(__file__))

        template = open(curr_dir + '/action_template.html', 'r')

        html = str(template.read())
        template.close()

        html = html.replace('<!-- Theme -->', theme)
        html = html.replace('<!-- Index -->', index)

        return html
