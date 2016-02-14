"""
Lazy loading file browsing tree
"""

from yapsy.IPlugin import IPlugin
from bottle import abort
import os
import json

class FaRegview(IPlugin):

    def __init__(self):
        self._display_name = 'File Tree'
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
        allowed = [ 'application/octet-stream' ]
        return str(evidence['mimetype']).lower() in allowed

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        if 'mode' in request.query and request.query['mode'] == 'children':
            if 'parent' not in request.query:
                abort(200, 'Bad request, mode children requires a parent in the form of a Path ID')
            request_file = helper.db_util.get_file_from_ppid(request.query['parent'])
            return self.get_child(request_file, helper)
        elif 'mode' in request.query and request.query['mode'] == 'root':
            return json.dumps([{
                    'title': evidence['name'],
                    'key': evidence['pid'],
                    'folder': True,
                    'lazy': True,
                    }], sort_keys=True)

        child_plugins = ''

        if children and evidence['image_id'] in children:
            child_plugins = str(children).split(evidence['image_id'])[0]
        if not child_plugins:
            child_plugins = 'fa_loader/fa_filedirectory/fa_fileanalyze/'
        if not children:
            children = 'fa_loader/fa_filedirectory/fa_fileanalyze/'

        if request.query_string:
            query_string = "?" + request.query_string
        else:
            query_string = ""

        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/filetree_template.html', 'r')
        html = str(template.read())
        html = html.replace("<!-- Path -->", evidence['pid'])
        if str(children).startswith(evidence['image_id']):
            html = html.replace('<!-- Home -->', "/plugins/" + child_plugins + children + query_string)
        else:
            html = html.replace('<!-- Home -->', "/plugins/" + children + query_string)
        html = html.replace('<!-- Child -->', "/plugins/" + child_plugins)
        html = html.replace('<!-- Query -->', query_string)
        html = html.replace('<!-- Name -->', 'Navigate')
        template.close()

        return html

    def get_child(self, evidence, helper):
        """Returns JSON list containing sub keys using Fancy Tree format"""
        children = []

        if evidence['meta_type'] != 'Directory':
            return json.dumps(children)

        #curr_folder = evidence['path'] + "/"

        for item in helper.db_util.query(evidence):
            source = item['_source']
            #TODO: Need to find out why there are weird ';' entries in the root of log2timeline
            if source['meta_type'] == 'Directory' and ';' not in source['iid']:
                folder = True
            else:
                folder = False

            #REMOVE TO SHOW ALL, TODO: Make this an option
            if folder:
                child = {
                        'title': source['name'],
                        'key': source['pid'],
                        'lazy': folder,
                        'folder': folder
                        }
                children.append(child)

        children.sort()
        return json.dumps(children)
