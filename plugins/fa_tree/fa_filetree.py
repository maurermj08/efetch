"""
Lazy loading file browsing tree
"""

from yapsy.IPlugin import IPlugin
from bottle import abort
import os
import json

class FaRegview(IPlugin):

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
        return "File Tree"

    def check(self, curr_file, path_on_disk, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        allowed = [ 'application/octet-stream' ]
        return str(mimetype).lower() in allowed

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

    def get(self, curr_file, helper, path_on_disk, mimetype, size, address, port, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        if 'mode' in request.query and request.query['mode'] == 'children':
            if 'parent' not in request.query:
                abort(200, 'Bad request, mode children requires a parent in the form of a Path ID')
            request_file = helper.db_util.get_file_from_ppid(request.query['parent'])
            return self.get_child(request_file, helper)
        elif 'mode' in request.query and request.query['mode'] == 'root':
            return json.dumps([{
                    'title': curr_file['image_id'] + ' at offset ' + curr_file['offset'] + '- ' + curr_file['path'],
                    'key': curr_file['pid'],
                    'folder': True,
                    'lazy': True,
                    }])

        child_plugins = ''

        if children and curr_file['image_id'] in children:
            child_plugins = str(children).split(curr_file['image_id'])[0]
        if not child_plugins:
            child_plugins = 'fa_loader/fa_filedirectory/fa_file_analyze/'
        if not children:
            children = 'fa_loader/fa_filedirectory/fa_file_analyze/'

        if request.query_string:
            query_string = "?" + request.query_string
        else:
            query_string = ""

        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/filetree_template.html', 'r')
        html = str(template.read())
        html = html.replace("<!-- Path -->", curr_file['image_id'] + '/' + curr_file['offset'] + '/' + curr_file['path'])
        if str(children).startswith(curr_file['image_id']):
            html = html.replace('<!-- Home -->', "http://" + address + ":" + port + "/plugins/" + child_plugins + children + query_string)
        else:
            html = html.replace('<!-- Home -->', "http://" + address + ":" + port + "/plugins/" + children + query_string)
        html = html.replace('<!-- Child -->', "http://" + address + ":" + port + "/plugins/" + child_plugins)
        html = html.replace('<!-- Query -->', query_string)
        html = html.replace('<!-- Name -->', 'Navigate')
        template.close()

        return html

    def get_child(self, curr_file, helper):
        """Returns JSON list containing sub keys using Fancy Tree format"""
        children = []

        if curr_file['file_type'] != 'directory':
            return json.dumps(children)

        curr_folder = curr_file['path'] + "/"

        for item in helper.db_util.list_dir(helper.db_util.get_file(curr_file['image_id'], curr_file['offset'], curr_folder)):
            source = item['_source']
            if source['file_type'] == 'directory':
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

        return json.dumps(children)
