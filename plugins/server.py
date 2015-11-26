from reglib import *
from bottle import route, run, static_file, response, post, request
import json
import os
@route('/')
def index():
    index_path = os.path.dirname(os.path.realpath(__file__)) + "/index.html"
    fh = open(index_path,'r')
    page = fh.read()
    fh.close()
    return page

@route('/static/<filepath:path>')
def server_static(filepath):
    base_path = os.path.dirname(os.path.realpath(__file__)) + "/static"
    return static_file(filepath, root=base_path)

@route('/base.json')
def base_tree():
    data = get_sub_keys("") 
    #data = [ { 'title': 'node1', 'key': 1, 'folder': True, 'children': [ { 'title': 'child1', 'key': 2 }, { 'title': 'child2', 'key': 3 } ] }, { 'title': 'node2', 'key': 4, 'folder': True,  'children': [ { 'title': 'child3', 'key': 5 } ] } ]
    #data = [ { 'title': 'node1', 'key': 1, 'folder': True, 'lazy': True }, { 'title': 'node2', 'key': 4, 'folder': True, 'lazy': True } ]
    response.content_type = 'application/json'
    return json.dumps(data)

@route('/children.json')
def get_children():
    #data = { 'node1': [ { 'title': 'child1', 'key': 2 }, { 'title': 'child2', 'key': 3 } ], 'node2': [ { 'title': 'child3', 'key': 5 } ] } 
    node_id = request.query['node_id']
    response.content_type = 'application/json'
    if not node_id:
        return "[]"
    data = get_sub_keys(node_id)
    return json.dumps(data)

@route('/values.json')
def values():
    #data = { 'node1': [ { 'title': 'child1', 'key': 2 }, { 'title': 'child2', 'key': 3 } ], 'node2': [ { 'title': 'child3', 'key': 5 } ] } 
    node_id = request.query['node_id']
    response.content_type = 'application/json'
    if not node_id:
        return "[]"
    data = get_values(node_id)
    return json.dumps(data)

def get_sub_keys(key):
    registry = get_registry()
    subkeys = get_subkeys(key, registry)
    registry_keys =  []
    for subkey in subkeys:
        if len(key) > 0:
            fqkp = key + "\\" + subkey
        else:
            fqkp = subkey
        sk_ds = {'title': subkey, 'refKey': fqkp}
        if get_subkeys(fqkp):
            sk_ds['folder'] = True
            sk_ds['lazy'] = True
        registry_keys.append(sk_ds)
    return registry_keys


run(host='0.0.0.0', port=8080, debug=True)
