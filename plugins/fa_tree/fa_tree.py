"""
Lazy loading browsing tree
"""

from yapsy.IPlugin import IPlugin
from bottle import abort
import os
import json

class FaTree(IPlugin):

    def __init__(self):
        self._display_name = 'Tree'
        self._popularity = 0
        self._parent = True
        self._cache = False
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

    def get(self, evidence, helper, path_on_disk, request, children, files=True, directories=True, source_plugin='fa_tree'):
        """Returns the result of this plugin to be displayed in a browser"""
        mode = helper.get_request_value(request, 'mode', '')
        
        if mode == 'children':
            parent = helper.get_request_value(request, 'parent', '')
            if not parent:
                abort(200, 'Bad request, mode children requires a parent in the form of a Path ID')
            request_file = helper.db_util.get_file_from_ppid(parent)

            return self.get_child(request_file, helper, files, directories)
        elif mode == 'root' and not directories:
            return self.get_child(evidence, helper, files, directories)
        elif mode == 'root':
            return json.dumps([{
                    'title': evidence['name'],
                    'key': evidence['pid'],
                    'folder': True,
                    'lazy': True,
                    'icon': '/plugins/fa_thumbnail/' + evidence['pid']
                    }], sort_keys=True)

        child_plugins = ''

        if children and evidence['image_id'] in children:
            child_plugins = str(children).split(evidence['image_id'])[0]
        if not child_plugins:
            child_plugins = 'fa_loader/fa_dirbrowser/fa_analyze/'
        if not children:
            children = 'fa_loader/fa_dirbrowser/fa_analyze/'

        if request.query_string:
            query_string = "?" + request.query_string
        else:
            query_string = ""

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

    def get_child(self, evidence, helper, files=True, directories=True):
        """Returns JSON list containing sub keys using Fancy Tree format"""
        children = []

        if evidence['meta_type'] != 'Directory':
            return json.dumps(children)

        for evidence_item in helper.db_util.bool_query_evidence(evidence):
            append = False
            folder = False

            #TODO: Need to find out why there are weird ';' entries in the root of log2timeline
            if ';' not in evidence_item['iid']:
                if files and evidence_item['meta_type'] == 'File':
                    append = True
                elif directories and evidence_item['meta_type'] == 'Directory':
                    append = True
                    folder = True

            if append:
                children.append( {
                        'title': evidence_item['name'],
                        'key': evidence_item['pid'],
                        'lazy': folder,
                        'folder': folder,
                        'icon': '/plugins/fa_thumbnail/' + evidence_item['pid']
                        } )

        children.sort()
        return json.dumps(children)
