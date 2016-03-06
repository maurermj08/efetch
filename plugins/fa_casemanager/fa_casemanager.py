"""
Allows for the adding, deleting, and modifying of cases
"""

from yapsy.IPlugin import IPlugin
import os


class FaCasemanager(IPlugin):
    def __init__(self):
        self.display_name = 'Case Manager'
        self.popularity = 0
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

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 0

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        cases = helper.db_util.read_case()['hits']['hits']
        table = []
        for case in cases:
            source = case['_source']
            name = source['name']
            description = ""
            evidence_list = []
            if source['description']:
                description = source['description']
            if source['evidence']:
                evidence_list = source['evidence']
            table.append(
                '<tr><td>' + name + '</td><td>' + description + '</td><td>' + ','.join(evidence_list) + '</td></tr>')

        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/case_manager_template.html', 'r')
        html = str(template.read())
        template.close()

        html = html.replace('<!-- Table -->', '\n'.join(table))
        return html
