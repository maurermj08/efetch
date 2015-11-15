from bottle import route, run, request, static_file, abort
import subprocess
import os
import sys
import getopt
import time
import logging
import magic
from utils.efetch_helper import EfetchHelper
from utils.db_util import DBUtil
from yapsy.PluginManager import PluginManager
from bottle import abort
from elasticsearch import Elasticsearch
from elasticsearch import helpers

global address
global port
global output_dir
global max_cache
global icon_dir
global curr_dir
global plugin_manager
global max_download_size
global my_magic
global database
global elastic
global helper
global db_util

def main(argv):
    try: 
        opts, args = getopt.getopt(argv, "ha:p:o:s:dD:m:", ["help", "address=", "port=", "output=", "size=", "debug", "database=", "maxfilesize="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    global address
    global port
    global output_dir
    global max_cache
    global icon_dir
    global curr_dir
    global resource_dir
    global plugin_manager
    global max_download_size
    global my_magic
    global elastic
    global helper
    global db_util

    #Just in case support both magic libs
    try:
        my_magic = magic.Magic(mime = True)
    except:
        my_magic = magic.Magic(flags=magic.MAGIC_MIME_TYPE)

    #Default Values
    max_download_size = 100 #In MegaBytes
    address = "localhost"
    port = str(8080)
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    output_dir = curr_dir + "/cache/"
    resource_dir = curr_dir + "/resources/"
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    icon_dir = curr_dir + "/icons/"

    if not os.path.isdir(icon_dir):
        logging.error("Could not find icon directory " + icon_dir) 
        sys.exit(2)
    
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

    #TODO MOVE TO analyze
    # Basic Plugin Management
    plugin_manager = PluginManager()
    plugin_manager.setPluginPlaces([curr_dir + "/plugins/"])
    plugin_manager.collectPlugins()    
    for plugin in plugin_manager.getAllPlugins():
        plugin_manager.activatePluginByName(plugin.name)

    #Initialize utils
    helper = EfetchHelper(database)
    db_util = DBUtil()

    run(host=address, port=port)

@route('/resources/<resource_path:path>')
def get_resource(resource_path):
    """Returns any file in the resource directory"""
    #TODO: Need better security
    if '..' in str(resource_path):
        return
    else:
        full_path = resource_dir + resource_path
        res_dir = os.path.dirname(full_path)
        res_name = os.path.basename(full_path)    
        return static_file(res_name, root=res_dir)        

#TODO -1 MOVE TO PLUGIN
@route('/analyze/<image_id>/<offset>/<input_type>/<path_or_inode:path>')
@route('/analyze/<image_id>/<offset>/<input_type>/')
def analyze(image_id, offset, input_type, path_or_inode = '/'):
    """Provides a web view with all applicable plugins, defaults to most popular"""
    #Get file from database
    curr_file = helper.get_file(image_id, offset, input_type, path_or_inode)

    logging.debug("Analyzing file " + curr_file['name'])
    logging.debug("Found the following plugins - " + str(plugin_manager.getAllPlugins()))
    
    #Add Directoy link
    plugins = []
    plugins.append('<a href="http://' + address + ':' + port + '/directory/' + curr_file['image_id'] + '/' + curr_file['offset']  + '/p' + curr_file['path'] + '" target="frame">Directory</a><br>')

    #If file is less than max download (cache) size, cache it and analyze it
    if curr_file['inode'] and curr_file['file_type'] != 'directory' and int(curr_file['size']) / 1000000 <= max_download_size:
        file_cache_path = cache_file(curr_file)
        actual_mimetype = helper.get_mimetype(file_cache_path)
        actual_size = os.path.getsize(file_cache_path)
        #Order Plugins by populatiry from highest to lowest
        for pop in reversed(range(1, 11)):
            for plugin in plugin_manager.getAllPlugins():    
                if plugin.plugin_object.popularity() == pop:
                    #Check if plugin applies to curr file
                    if plugin.plugin_object.check(curr_file, file_cache_path, actual_mimetype, actual_size):
                        logging.debug("Check matched, adding plugin " + plugin.plugin_object.display_name())
                        plugins.append('<a href="http://' + address + ':' + port + '/plugin/' + plugin.name + '/' + curr_file['image_id'] + '/' + curr_file['offset'] + '/p' + curr_file['path'] + '" target="frame">' + plugin.plugin_object.display_name() + '</a><br>')
                    else:
                        logging.debug("Check did not match, NOT adding plugin " + plugin.plugin_object.display_name())
    else:
        actual_mimetype = '?'
        actual_size = '?'

    #Modifies HTML page
    html = ""
    template = open(curr_dir + '/template.html', 'r')
    html = str(template.read())
    html = html.replace('<!-- Home -->', "http://" + address + ":" + port + "/directory/" + curr_file['image_id'] + '/' + curr_file['offset']  + '/p' + curr_file['path'])
    if curr_file['file_type'] == 'directory':
        html = html.replace('<!-- File -->', curr_file['name']) 
        html = html.replace('<!-- Mimetype -->', 'Directory')
        html = html.replace('<!-- Size -->', str(curr_file['size']) + " Bytes")
        html = html.replace('<!-- Links -->', "\n".join(plugins))
    else: 
        html = html.replace('<!-- File -->', curr_file['name']) 
        html = html.replace('<!-- Mimetype -->', actual_mimetype)
        html = html.replace('<!-- Size -->', str(actual_size) + " Bytes")
        html = html.replace('<!-- Links -->', "\n".join(plugins))

    return html
    
@route('/plugin/<name>/')
@route('/plugin/<name>/<image_id>/')
@route('/plugin/<name>/<image_id>/<offset>/')
@route('/plugin/<name>/<image_id>/<offset>/<path:path>')
def plugin(name, image_id, offset, path):
    """Returns the iframe of the given plugin for the given file"""
    if path:
        #Get file from database
        curr_file = db_util.get_file(image_id, offset)
    
        #Cache file
        file_cache_path = plugin_manager.getPluginByName(curr_file['parser').cache_file(curr_file)

        #Get mimetype and size
        actual_mimetype = helper.get_mimetype(file_cache_path)
        actual_size = os.path.getsize(file_cache_path)
    else:
        curr_file = None
        file_cache_path = None
        actual_mimetype = None
        actual_size = None

    #Get Plugin
    plugin = plugin_manager.getPluginByName(str(name).lower())
    
    #Get Accept metadata
    accept=request.headers.get("Accept")

    #Return plugins frame
    return plugin.plugin_object.get(curr_file, database, file_cache_path, actual_mimetype, actual_size, address, port, request.query)

#TODO -1 MOVE TO PLUGIN
@route('/directory/<image_id>/<offset>/<input_type>')
@route('/directory/<image_id>/<offset>/<input_type>/')
@route('/directory/<image_id>/<offset>/<input_type>/<path:path>')
def directory(image_id, offset, input_type, path="/"):
    """Returns a formatted directory listing for the given path"""
    #Get file from database
    curr_file = db_util.get_file(image_id, offset, path)
    
    #Get cached file
    if curr_file['file_type'] != 'directory' and curr_file['inode']:
        file_cache_path = cache_file(curr_file)   

    #If path is a folder just set the view to it, if not use the files parent folder
    if curr_file['file_type'] == 'directory':
        curr_folder = curr_file['path'] + "/"
    else:
        curr_folder = curr_file['dir']

    listing = []
    #TODO: Change localtime to case time, specifically what is supplied to sleuthkit
    for item in database._dir[curr_folder]:        
        listing.append("    <tr>")  
        listing.append('        <td><img src="http://' + address + ':' + port + '/thumbnail/' + item['image_id'] + '/' + item['offset'] + '/p' + item['path'] + '" alt="-" style="width:32px;height:32px;"></td>')
        if item['file_type'] == 'directory':
            listing.append('        <td><a href="http://' + address + ':' + port + '/directory/' + item['image_id'] + '/' + item['offset'] + '/p' + item['path'] + '" target="_self">' + item['name'] + "</a></td>")
        else:
            listing.append('        <td><a href="http://' + address + ':' + port + '/analyze/' + item['image_id'] + '/' + item['offset'] + '/p' + item['path'] + '" target="_top">' + item['name'] + "</a></td>")
        if (item['mod']):
            listing.append("        <td>" + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(item['mod']))) + "</td>")
        else:
            listing.append("        <td> - </td>")
        if (item['acc']):
            listing.append("        <td>" + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(item['acc']))) + "</td>")
        else:
            listing.append("        <td> - </td>")
        if (item['chg']):
            listing.append("        <td>" + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(item['chg']))) + "</td>")
        else:
            listing.append("        <td> - </td>")
        if (item['cre']):
            listing.append("        <td>" + time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(float(item['cre']))) + "</td>")
        else:
            listing.append("        <td> - </td>")
        listing.append("        <td>" + item['size'] + "</td>")
        listing.append("    </tr>")  

    html = ""
    template = open(curr_dir + '/dir_template.html', 'r')
    html = str(template.read())
    html = html.replace('<!-- Table -->', '\n'.join(listing))

    return html

#TODO -1 MOVE TO PLUGIN
@route('/thumbnail/<image_id>/<offset>/<input_type>/')
@route('/thumbnail/<image_id>/<offset>/<input_type>/<path:path>')
def thumbnail(image_id, offset, input_type, path='/'):
    """Returns either an icon or thumbnail of the provided file"""
    #Get file from database
    curr_file = db_util.get_file(image_id, offset, path)
    
    #If it is folder just return the folder icon
    if curr_file['file_type'] == 'directory' or str(curr_file['name']).strip() == "." or str(curr_file['name']).strip() == "..":
        return static_file("_folder.png", root=icon_dir, mimetype='image/png')

    #Uses extension to determine if it should create a thumbnail
    assumed_mimetype = helper.guess_mimetype(str(curr_file['ext']).lower())

    #If the file is an image create a thumbnail
    if assumed_mimetype.startswith('image'):
        #Cache file
        file_cache_path = cache_file(curr_file)   	 
        thumbnail_cache_path = output_dir + 'thumbnails/' + curr_file['iid'] + '/' + curr_file['name']
        thumbnail_cache_dir = output_dir + 'thumbnails/' + curr_file['iid'] + '/'
        #TODO: If this is always a jpeg just state it, should save some time
        thumbnail_mimetype = helper.get_mimetype(thumbnail_cache_path)
        
        if os.path.isfile(thumbnail_cache_path):
            return static_file(curr_file['name'], root=thumbnail_cache_dir, mimetype=thumbnail_mimetype)
        else:
            return static_file('_missing.png', root=icon_dir, mimetype='image/png')
    #If file is not an image return the icon associated with the files extension
    else:
        if not os.path.isfile(icon_dir + str(curr_file['ext']).lower() + ".png"):
            return static_file("_blank.png", root=icon_dir, mimetype='image/png')
        else:
            return static_file(curr_file['ext'] + ".png", root=icon_dir, mimetype='image/png')

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
