"""
Listens and sends any changes to the current evidence item
"""

from yapsy.IPlugin import IPlugin
import os


class FaListener(IPlugin):
    def __init__(self):
        self.display_name = 'Listener'
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
        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/listener_template.html', 'r')
        html = str(template.read())
        query_string = helper.get_query_string(request)

        html = html.replace('<!-- Home -->', "/plugins/" + children + query_string)
        html = html.replace('<!-- PID -->', evidence['pid'])
        html = html.replace('<!-- QUERY -->', query_string)
        html = html.replace('<!-- PLUGINS -->', "/plugins/" + children.split(evidence['image_id'], 1)[0])

        return html
