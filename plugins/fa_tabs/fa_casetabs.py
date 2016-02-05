"""
Displays case manager and open cases in tabs
"""

from yapsy.IPlugin import IPlugin
import os

class FaCasetabs(IPlugin):

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
        return "Case Tabs"

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
        return True

    def get(self, curr_file, helper, path_on_disk, mimetype, size, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/tabs_template.html', 'r')
        html = str(template.read())

        if request.query_string:
            query_string = "?" + request.query_string
        else:
            query_string = ""

        cases = []
        cases.append('       <div title="Demo" style="height:100%;width:100%">')
        cases.append('           <iframe src="/plugins/' + children + query_string + '?case=test">')
        cases.append('           </iframe>')
        cases.append('       </div>')

        html = html.replace('<!-- Home -->', "/plugins/fa_casemanager/")
        html = html.replace('<!-- Cases -->', '\n'.join(cases))
        
        return html

