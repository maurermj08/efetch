"""
AJAX for Registry Viewer plugin
"""

from yapsy.IPlugin import IPlugin
from bottle import route, run, static_file, response, post, request, abort
from Registry import Registry
import binascii
import json
import os

class FaRegviewAjax(IPlugin):
    def __init__(self):
        self.display_name = 'Regview Ajax'
        self.popularity = 0
        self.parent = False
        self.cache = True
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
        return "application/json"

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
        data = get_values(node_id, path_on_disk)
        return json.dumps(data)

    def get_sub_keys(self, key, path_on_disk):
        registry = get_registry(path_on_disk)
        subkeys = get_subkeys(key, registry)
        registry_keys = []
        for subkey in subkeys:
            if len(key) > 0:
                fqkp = key + "\\" + subkey
            else:
                fqkp = subkey
            sk_ds = {'title': subkey, 'refKey': fqkp}
            if get_subkeys(fqkp, registry):
                sk_ds['folder'] = True
                sk_ds['lazy'] = True
            registry_keys.append(sk_ds)
        return registry_keys


def get_registry(pod):
    return Registry.Registry(pod)


def parse_reg(key, depth=0):
    reg_str = '\t' * depth + key.path() + "\n"
    if depth < 6:
        for subkey in key.subkeys():
            reg_str += parse_reg(subkey, depth + 1)
    return reg_str


def get_values(key_name, pod):
    #for value in [v for v in key.values() if v.value_type() == Registry.RegSZ or v.value_type() == Registry.RegExpandSZ]:
    reg = get_registry(pod)
    results = []
    try:
        key = reg.open(key_name)
        for value in key.values():
            if value.value_type_str() == "RegBin":
                results.append({ 'name': value.name(), 'type': value.value_type_str(), 'value': "0x" + str(binascii.hexlify(value.value())) })
            else:
                results.append({ 'name': value.name(), 'type': value.value_type_str(), 'value': value.value() })
        return results
    except Registry.RegistryKeyNotFoundException:
        print("Error: couldn't find the key: " + key_name)
        return None


def get_subkeys(key_name, reg):
    try:
        subkeys = []
        key = reg.open(key_name)
        for subkey in key.subkeys():
            subkeys.append(subkey.name())
        return subkeys
    except Registry.RegistryKeyNotFoundException:
        print("Error: couldn't find the key: " + key_name)
        return None