"""
Lazy loading browsing tree
"""

from yapsy.IPlugin import IPlugin
from bottle import abort
import os
import json


class FaTree(IPlugin):
    def __init__(self):
        self.display_name = 'Tree'
        self.popularity = 0
        self.parent = True
        self.cache = False
        self._default_child = 'fa_loader/fa_dirbrowser/fa_analyze/'
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

    def get(self, evidence, helper, path_on_disk, request, children, files=True, directories=True,
            source_plugin='fa_tree'):
        """Returns the result of this plugin to be displayed in a browser"""
        mode = helper.get_request_value(request, 'mode', '')
        filter_query = helper.get_filter(request)

        if mode == 'children':
            parent = helper.get_request_value(request, 'parent', '')
            if not parent:
                abort(200, 'Bad request, mode children requires a parent in the form of a Path ID')
            request_file = helper.db_util.get_file_from_pid(parent)

            return self.get_child(request_file, helper, files, directories, filter_query)
        elif mode == 'root' and not directories:
            return self.get_child(evidence, helper, files, directories, filter_query)
        elif mode == 'root':
            return json.dumps([{
                'title': evidence['file_name'],
                'key': evidence['pid'],
                'folder': True,
                'lazy': True,
                'icon': '/plugins/fa_thumbnail/' + evidence['pid']
            }], sort_keys=True)

        child_plugins = helper.get_children(evidence['image_id'], children, self._default_child)
        if not children:
            children = self._default_child

        query_string = helper.get_query_string(request)

        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/tree_template.html', 'r')
        html = str(template.read())
        html = html.replace("<!-- Path -->", evidence['pid'])
        if str(children).startswith(evidence['image_id']):
            html = html.replace('<!-- Home -->', "/plugins/" + child_plugins + children + query_string)
        else:
            html = html.replace('<!-- Home -->', "/plugins/" + children + query_string)
        html = html.replace('<!-- Child -->', "/plugins/" + child_plugins)
        html = html.replace('<!-- Query -->', query_string)
        html = html.replace('<!-- Name -->', 'Navigate')
        html = html.replace('<!-- Plugin -->', source_plugin)
        html = html.replace('<!-- Files -->', str(files))
        html = html.replace('<!-- Directories -->', str(directories))
        template.close()

        return html

    def get_child(self, evidence, helper, files=True, directories=True, filter_query={}):
        """Returns JSON list containing sub keys using Fancy Tree format"""
        children = []

        if evidence['meta_type'] != 'Directory':
            return json.dumps(children)

        if directories:
            for evidence_item in helper.db_util.bool_query_evidence(evidence, {'must': {'term': {'meta_type':'Directory'}}}):
                # TODO: Need to find out why there are weird ';' entries in the root of log2timeline
                if ';' not in evidence_item['iid']:
                    children.append({
                        'title': evidence_item['name'],
                        'key': evidence_item['pid'],
                        'lazy': True,
                        'folder': True,
                        'icon': '/plugins/fa_thumbnail/' + evidence_item['pid']
                    })

        if files:
            filter_query = helper.db_util.append_dict(filter_query, 'must', {'term': {'meta_type':'File'}})
            for evidence_item in helper.db_util.bool_query_evidence(evidence, filter_query):
                # TODO: Need to find out why there are weird ';' entries in the root of log2timeline
                if ';' not in evidence_item['iid']:
                    children.append({
                        'title': evidence_item['name'],
                        'key': evidence_item['pid'],
                        'lazy': False,
                        'folder': False,
                        'icon': '/plugins/fa_thumbnail/' + evidence_item['pid']
                    })

        children.sort()
        return json.dumps(children)
