"""
Displays case manager and open cases in tabs
"""

from yapsy.IPlugin import IPlugin
import os


class FaCasetabs(IPlugin):
    def __init__(self):
        self.display_name = 'Case Tabs'
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
