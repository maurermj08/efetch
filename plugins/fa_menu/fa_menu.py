"""
Simple menu bar
"""

from yapsy.IPlugin import IPlugin
import os

class FaMenu(IPlugin):

    def __init__(self):
        self._display_name = 'Menu'
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
        """Returns the result of this plugin to be displayed in a browser"""
        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/menu_template.html', 'r')
        html = str(template.read())

        if request.query_string:
            query_string = "?" + request.query_string
        else:
            query_string = ""

        html = html.replace('<!-- Home -->', "/plugins/" + children + query_string)
        html = html.replace('<!-- Upload -->', "/plugins/fa_upload")
        html = html.replace('<!-- Case -->', request.query['case'])

        return html
