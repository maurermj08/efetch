"""
CRUD for Efetch Cases
"""

from yapsy.IPlugin import IPlugin
from bottle import route, run, static_file, response, post, request, abort
import json


class FaCase(IPlugin):
    def __init__(self):
        self.display_name = 'Case API'
        self.popularity = 0
        self.parent = False
        self.cache = False
        self._default_child = 'fa_header'
        self._default_children = '/fa_menu/fa_casetree/fa_dirtree/fa_filebrowser/fa_analyze/'
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        return False

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        method = helper.get_request_value(request, 'method', False)

        if not 'method':
            abort(400, 'No method specified')

        name = helper.get_request_value(request, 'name', False)
        description = helper.get_request_value(request, 'description', False)
        new_name = helper.get_request_value(request, 'new_name', False)
        evidence_list = helper.get_request_value(request, 'evidence', [])

        if evidence_list:
            evidence_list = evidence_list.split()

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
                result_table.append({"evidence": item})
            return {"rows": result_table, "total": len(result_table)}
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
        #TODO
        elif method == 'open':
            result = helper.db_util.get_evidence(name)
            result_table = []
            for item in result:
                result_table.append({'term': {'image_id': item}})
            new_request = {'bool' : {'should': result_table}}
            return helper.plugin_manager.getPluginByName(self._default_child).plugin_object.get(evidence, helper,
                                                                                                path_on_disk, new_request,
                                                                                                self._default_child)

        return abort(400, 'Unknown method')

    def read_table(self, result):
        cases = []
        for hit in result['hits']['hits']:
            cases.append(hit['_source'])

        table = {"rows": cases, "total": len(cases)}

        return table
