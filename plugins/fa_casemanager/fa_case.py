"""
CRUD for Efetch Cases
"""

from yapsy.IPlugin import IPlugin
from bottle import route, run, static_file, response, post, request, abort
import json

class FaCase(IPlugin):

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
        return "Case API"

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        return False

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 0

    def parent(self):
        """Returns if the plugin accepts other plugins (True) or only files (False)"""
        return False

    def cache(self):
        """Returns if caching is required"""
        return False

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        if "method" not in request.query and not request.forms.get('method'):
            abort(400, 'No method specified')

        if "method" in request.query:
            method = request.query['method']
        else:
            method = request.forms.get('method')
        if "name" in request.query:
            name = request.query['name']
        else:
            name = request.forms.get('name')
        if "description" in request.query:
            description = request.query['description']
        else:
            description = request.forms.get('description')
        if "new_name" in request.query:
            new_name = request.query['new_name']
        else:
            new_name = request.forms.get('new_name')
        #TODO: Determine if this is the best way to get a list
        if "evidence" in request.query:
            evidence_list = request.query['evidence'].split(',')
        elif request.forms.get('evidence'):
            evidence_list = request.forms.get('evidence').split(',')
        else:
            evidence_list = []

        if method == "read":
            return helper.db_util.read_case(name)
        elif method == "read_table":
            return self.read_table(helper.db_util.read_case())
        elif method == "add_evidence":
            return helper.db_util.add_evidence_to_case(name, evidence_list)
        elif method == "get_evidence":
            result = helper.db_util.get_evidence(name)
            result_table = []
            for item in result:
                result_table.append({ "evidence" : item })
            return {"rows" : result_table, "total" : len(result_table) }
        elif not name:
            abort(400, 'No name specified')
        elif method == "remove_evidence":
            return helper.db_util.remove_evidence_from_case(name, evidence_list)
        elif method == "create":
            return helper.db_util.create_case(name, description, evidence_list)
        elif method == "update":
            return helper.db_util.update_case(name, new_name, description, evidence_list)
        elif method == "delete":
            return helper.db_util.delete_case(name)

        return abort(400, 'Unknown method')

    def read_table(self, result):
        cases = []
        for hit in result['hits']['hits']:
            cases.append(hit['_source'])

        table = {"rows" : cases, "total" : len(cases) }

        return table
