"""
Basic Kibana Plugin
"""

from yapsy.IPlugin import IPlugin
import os
import rison


class FaKibana(IPlugin):

    def __init__(self):
        self.display_name = 'Kibana'
        self.popularity = 0
        self.parent = True
        self.cache = False
        self._default_child = 'fa_analyze/'
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
        child_plugins = helper.get_children(evidence['image_id'], children, self._default_child)

        if not children:
            children = self._default_child
        query_string = helper.get_query_string(request)

        filter_query = helper.get_filter(request)

        if filter_query:
            query = { 'bool': filter_query }
            print('JSON: ' + str(query))
            query = rison.dumps(query)
        else:
            query = "(query_string:(analyze_wildcard:!t,query:'*'))"

        print('RISON: ' + str(query))
        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/kibana_template.html', 'r')
        html = str(template.read())
        if str(children).startswith(evidence['image_id']):
            html = html.replace('<!-- Home -->', "/plugins/" + child_plugins + children + query_string)
        else:
            html = html.replace('<!-- Home -->', "/plugins/" + children + query_string)

        html = html.replace('<!-- Query -->', query)
        html = html.replace('<!-- Index -->', 'efetch_evidence_' + evidence['image_id'])
        return html
