from bottle import route, run, request, static_file, abort
import os
import sys
import getopt
import logging
import json
from utils.efetch_helper import EfetchHelper

global address
global port
global max_cache
global plugin_manager
global max_download_size
global elastic
global helper

def main(argv):
    try: 
        opts, args = getopt.getopt(argv, "ha:p:o:s:dD:m:", ["help", "address=", "port=", "output=", "size=", "debug", "database=", "maxfilesize="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    global address
    global port
    global max_cache
    global plugin_manager
    global max_download_size
    global elastic
    global helper

    #Default Values
    max_download_size = 100 #In MegaBytes
    address = "localhost"
    port = "8080"

    curr_dir = os.path.dirname(os.path.realpath(__file__))
    output_dir = curr_dir + "/cache/"
    upload_dir = curr_dir + "/uploads/"
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-a", "--address"):
            address = arg
        elif opt in ("-p", "--port"):
            port = str(arg)
        elif opt in ("-o", "--output"):
            output_dir = arg
        elif opt in ("-s", "--size"):
            max_cache = arg    
        elif opt in ('-d', "--debug"):
            logging.basicConfig(level=logging.DEBUG)
        elif opt in ('-m', "--maxfilesize"):
            max_download_size = arg
        else:
            logging.error("Unknown argument " + opt)
            usage()
            sys.exit(2)
    
    if not output_dir.endswith("/"):
        output_dir = output_dir + "/"
    if not os.path.isdir(output_dir):
        logging.error("Could not find output directory " + output_dir)
        sys.exit(2)

    #Initialize utils
    helper = EfetchHelper(curr_dir, output_dir, upload_dir, max_download_size * 1000000)
    test = helper.db_util
    manager = helper.plugin_manager

    run(host=address, port=port)

@route('/resources/<resource_path:path>')
def get_resource(resource_path):
    """Returns any file in the resource directory"""
    #TODO: Need better security
    if '..' in str(resource_path):
        return
    else:
        full_path = helper.resource_dir + resource_path
        res_dir = os.path.dirname(full_path)
        res_name = os.path.basename(full_path)    
        return static_file(res_name, root=res_dir)        

@route('/')
def index():
    """Returns the home page for Efetch"""
    return get_resource('cases_table.html')

@route('/plugins/')
def list_plugins():
    """Returns a json object of all the plugins"""
    plugin_list = []

    for plugin in helper.plugin_manager.getAllPlugins():
        plugin_list.append(plugin.name)
    
    return json.dumps(plugin_list)

@route('/plugins/<args:path>')
@route('/plugins/<args:path>', method='POST')
def plugins(args):
    """Returns the iframe of the given plugin for the given file"""
    file_cache_path = None
    actual_mimetype = None
    actual_size = None

    args_list = args.split('/')

    name = str(args_list.pop(0))
    plugin = helper.plugin_manager.getPluginByName(str(name).lower())

    if not plugin:
        abort(404, "Sorry, could not find plugin " + str(name).lower())
        
    curr_file = None
    file_cache_path = None
    actual_mimetype = None
    actual_size = None
    children = None

    if plugin.plugin_object.parent():
        children = '/'.join(args_list)
        #Updates the args list so parent plugins can get imaged_id,  and path
        while args_list and helper.plugin_manager.getPluginByName(args_list[0]) and helper.plugin_manager.getPluginByName(args_list[0]).plugin_object.parent():
            args_list.pop(0)
        if args_list and helper.plugin_manager.getPluginByName(args_list[0]):
            args_list.pop(0)

    #Image ID
    if args_list:
        image_id = args_list.pop(0)
    else:
        image_id = None

    #Path
    if args_list:
        path = '/'.join(args_list)
    else:
        path = ''
    
    if image_id:
        #Get file from database
        try:
            curr_file = helper.db_util.get_file(image_id, image_id + '/' + str(path))
        except:
            abort(404, 'File "' + str(path) + '" not found for image "' + image_id + '"')

        #Cache file
        if plugin.plugin_object.cache():
            file_cache_path = helper.cache_file(curr_file)
      
        if file_cache_path:
            #Get mimetype and size
            actual_mimetype = helper.get_mimetype(file_cache_path)
            actual_size = os.path.getsize(file_cache_path)

    #Get Accept metadata
    accept=request.headers.get("Accept")
    
    #Return plugins frame
    return plugin.plugin_object.get(curr_file, helper, file_cache_path, actual_mimetype, actual_size, request, children)

def usage():
    print("usage: efetch.py [-h] [-a ADDRESS] [-p PORT] [-o DIR ] [-s SIZE] [-d] [-D DATABASE] [-m maxfilesize]")
    print("")
    print("efetch is a simple webserver that can return files and thumbnails from an image.")
    print("!!!WARNING!!! there are major known security issues if this is run as root and externally facing!")
    print("")
    print("optional arguments:")
    print("  -h, --help         shows this help message and exits")
    print("  -a, --address      sets the IP address or hostname this server runs on, defaults to localhost")
    print("  -p, --port         sets the port this server runs on, defaults to 8080")
    print("  -o, --output       directory to store output files")
    print("  -s, --size         the max size of cache storage, defaults to 1GB [NOT IMPLEMENTED]")
    print("  -d, --debug        displays debug output")
    print("  -D, --database     use an existing database file")
    print("  -m, --maxfilesize  max file size to download when caching files")
    print("")

if __name__=="__main__":
    main(sys.argv[1:])
