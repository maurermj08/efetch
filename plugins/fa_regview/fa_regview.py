"""
Lazy loading registry viewer
"""

from yapsy.IPlugin import IPlugin
import os

class FaRegview(IPlugin):

    def __init__(self):
        self._display_name = 'Reg. View'
        self._popularity = 8
        self._parent = False
        self._cache = True
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        allowed = [ 'application/octet-stream' ]
        return str(evidence['mimetype']).lower() in allowed

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/regview_template.html', 'r')
        html = str(template.read())
        html = html.replace("<!-- Path -->", evidence['pid'])
        template.close()
 
        return html
