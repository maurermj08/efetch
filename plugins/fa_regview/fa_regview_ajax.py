"""
AJAX for Registry Viewer plugin
"""

from yapsy.IPlugin import IPlugin
from bottle import route, run, static_file, response, post, request, abort
import json
import os
import reglib

class FaRegviewAjax(IPlugin):

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
        return "Regview Ajax"

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "application/json"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 0

    def parent(self):
        """Returns if the plugin accepts other plugins (True) or only files (False)"""
        return False

    def cache(self):
        """Returns if caching is required"""
        return True

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        method = request.query['method']

        if not method:
            abort(400, 'No method specified')
        elif method == "base":
            return self.base_tree(path_on_disk)
        elif method == "children":
            return self.get_children(request, path_on_disk)
        elif method == "values":
            return self.values(request, path_on_disk)
        
        return abort(400, 'Unknown method')
    
    def base_tree(self, path_on_disk):
        data = self.get_sub_keys("", path_on_disk) 
        response.content_type = 'application/json'
        return json.dumps(data)

    def get_children(self, request, path_on_disk):
        node_id = request.query['node_id']
        response.content_type = 'application/json'
        if not node_id:
            return "[]"
        data = self.get_sub_keys(node_id, path_on_disk)
        return json.dumps(data)

    def values(self, request, path_on_disk):
        node_id = request.query['node_id']
        response.content_type = 'application/json'
        if not node_id:
            return "[]"
        data = reglib.get_values(node_id, path_on_disk)
        return json.dumps(data)

    def get_sub_keys(self, key, path_on_disk):
        registry = reglib.get_registry(path_on_disk)
        subkeys = reglib.get_subkeys(key, registry)
        registry_keys =  []
        for subkey in subkeys:
            if len(key) > 0:
                fqkp = key + "\\" + subkey
            else:
                fqkp = subkey
            sk_ds = {'title': subkey, 'refKey': fqkp}
            if reglib.get_subkeys(fqkp, registry):
                sk_ds['folder'] = True
                sk_ds['lazy'] = True
            registry_keys.append(sk_ds)
        return registry_keys
