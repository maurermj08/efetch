"""
Displays all primary evidence in a case in a tree view
"""

from yapsy.IPlugin import IPlugin
import os

class FaCasetree(IPlugin):

    def __init__(self):
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def display_name(self):
        """Returns the name displayed in the webview"""
        return "Case Tree View"

    def check(self, curr_file, path_on_disk, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 0

    def parent(self):
        """Returns if the plugin accepts other plugins (True) or only files (False)"""
        return True

    def cache(self):
        """Returns if caching is required"""
        return False

    def get(self, curr_file, helper, path_on_disk, mimetype, size, address, port, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        child_plugins = ''

        if children and curr_file['image_id'] in children:
            child_plugins = str(children).split(curr_file['image_id'])[0]
        if not child_plugins:
            child_plugins = 'fa_loader/fa_filedirectory/fa_file_analyze/'
        if not children:
            children = 'fa_loader/fa_filedirectory/fa_file_analyze/'

        if request.query_string:
            query_string = "?" + request.query_string
        else:
            query_string = ""

        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/casetree_template.html', 'r')
        html = str(template.read())
        html = html.replace("<!-- Path -->", curr_file['image_id'] + '/' + curr_file['offset'] + '/' + curr_file['path'])
        if str(children).startswith(curr_file['image_id']):
            html = html.replace('<!-- Home -->', "http://" + address + ":" + port + "/plugins/" + child_plugins + children + query_string)
        else:
            html = html.replace('<!-- Home -->', "http://" + address + ":" + port + "/plugins/" + children + query_string)
        html = html.replace('<!-- Child -->', "http://" + address + ":" + port + "/plugins/" + child_plugins + query_string)
        html = html.replace('<!-- Name -->', 'Evidence')
        template.close()

        return html
