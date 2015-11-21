from bottle import route, run, request, static_file
import os
import sys
import getopt
import logging
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
    port = str(8080)

    #MOVE DIRS TO HELPER (NOT CURR & OUTPUT)
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    output_dir = curr_dir + "/cache/"
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
    helper = EfetchHelper(curr_dir, output_dir, max_download_size * 1000000)
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

@route('/plugins/<name>/')
def plugin_empty(name):
    """Returns the iframe of the given plugin for the given file"""
    #Get Plugin
    plugin = helper.plugin_manager.getPluginByName(str(name).lower())
    
    curr_file = None
    file_cache_path = None
    actual_mimetype = None
    actual_size = None

    #Get Accept metadata
    accept=request.headers.get("Accept")

    #Return plugins frame
    return plugin.plugin_object.get(curr_file, helper, file_cache_path, actual_mimetype, actual_size, address, port, request.query)


@route('/plugins/<name>/<image_id>/<offset>/')
def plugin(name, image_id, offset):
    """Returns the iframe of the given plugin for the given file"""
    return plugin(name, image_id, offset, u'/')

#@route('/plugins/<name>/<image_id>/')
@route('/plugins/<name>/<image_id>/<offset>/<path:path>')
def plugin(name, image_id, offset, path):
    """Returns the iframe of the given plugin for the given file"""
    file_cache_path = None
    actual_mimetype = None
    actual_size = None
    if path == 'p/':
        path = '/'

    #Get Plugin
    plugin = helper.plugin_manager.getPluginByName(str(name).lower())
   
    if not plugin:
        abort(404, "Sorry, could not find plugin " + str(name).lower())

    if path:
        #Get file from database
        curr_file = helper.db_util.get_file(image_id, offset, str(path))
    
        #Cache file
        if plugin.plugin_object.cache():
            file_cache_path = helper.cache_file(curr_file)
      
        if file_cache_path:
            #Get mimetype and size
            actual_mimetype = helper.get_mimetype(file_cache_path)
            actual_size = os.path.getsize(file_cache_path)
    else:
        curr_file = None
        file_cache_path = None
        actual_mimetype = None
        actual_size = None

    #Get Accept metadata
    accept=request.headers.get("Accept")

    #Return plugins frame
    return plugin.plugin_object.get(curr_file, helper, file_cache_path, actual_mimetype, actual_size, address, port, request.query)

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
