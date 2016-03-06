"""
Gets an overview of the file without using cache
"""

from yapsy.IPlugin import IPlugin
import os


class FaOverview(IPlugin):
    def __init__(self):
        self.display_name = 'Overview'
        self.popularity = 10
        self.parent = False
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

        listing = []

        for item in evidence:
            listing.append('<tr><td>' + str(item) + '</td><td>' + str(evidence[item]) + '</td></tr>')

        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/overview_template.html', 'r')
        html = str(template.read())
        template.close()

        html = html.replace('<!-- Table -->', '\n'.join(listing))

        return html
