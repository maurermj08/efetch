from bottle import route, run, request, static_file, abort
import subprocess
import os
import sys
import getopt
import time
import pytsk3
import logging
import magic
from pydblite import Base
from PIL import Image
from utils.efetch_helper import EfetchHelper
from yapsy.PluginManager import PluginManager
from bottle import abort

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
global helper

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
    global database
    global helper

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
    database_file = None
 
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
        elif opt in ("-D", "--database"):
            database_file = arg
        elif opt == '-d':
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.error("Unknown argument " + opt)
            usage()
            sys.exit(2)
    
    if not output_dir.endswith("/"):
        output_dir = output_dir + "/"
    if not os.path.isdir(output_dir):
        logging.error("Could not find output directory " + output_dir)
        sys.exit(2)
    if database_file and not os.path.isfile(database_file):
        logging.error("Could not find database file " + database_file)
        sys.exit(2)

    if database_file:
        database = Base(database_file)
        if database.exists():
            database.open()
            database.create(mode='open')
        else:
            logging.error("Failed to open Database " + database_file)
            sys.exit(2)
    else:
        database = Base(str(int(round(time.time() * 1000))) + '.pd1')
        if database.exists():
            database.open()
        else:
            database.create('id', 'pid', 'iid', 'image_id', 'offset', 'image_path', 'name', 'path', 'ext', 'dir', 'file_type', 'inode', 'mod', 'acc', 'chg', 'cre', 'size', 'uid', 'gid')
            database.create_index('id')
            database.create_index('pid')
            database.create_index('iid')
            database.create_index('image_id')
            database.create_index('dir')
        logging.debug("Saved database")

    #TODO MOVE TO analyze
    # Basic Plugin Management
    plugin_manager = PluginManager()
    plugin_manager.setPluginPlaces([curr_dir + "/plugins/"])
    plugin_manager.collectPlugins()    
    for plugin in plugin_manager.getAllPlugins():
        plugin_manager.activatePluginByName(plugin.name)

    helper = EfetchHelper(database)

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

@route('/image/add/<image_id>/<offset>/<image_path:path>')
def add_image(image_id, offset, image_path):
    """Creates a file listing of the partition at the provided image and offset in the database"""
    image_path = "/" + image_path

    #Error Handling
    if database._image_id[image_id] and database._image_id[image_id][0]["path"] != str(image_path):
        logging.error("Image ID '" + image_id + "' already in use")
        abort(400, "That Image ID is already in use by an image with a different path")
    if database._id[image_id + "/" + offset]:
        logging.error("Image '" + image_id + "' with offset '" + offset + "' already exists")
        abort(400, "Database already contains an image with that ID and offset")
    if not os.path.isfile(image_path):
        logging.error("Could not find file at path '" + str(image_path) + "'")
        abort(400, "Could not find file at specified path '" + str(image_path) + "'")
        
    logging.info("Adding image to databse")
    
    try:
        image = pytsk3.Img_Info(url=image_path)
        file_system = pytsk3.FS_Info(image)
        database.insert(image_id + "/" + offset, image_id + '/' + offset + '/', image_id + '/' + offset + '/-1', image_id, offset, image_path, '/', '', '', '', 'directory', -1, 0, 0, 0, 0, 0, 0, 0)
        load_database(file_system, image_id, offset, image_path, database, "/")
        database.commit()
    except:
        logging.error("Failed to parse image '" + image_path + "' at offset '" + offset + "'")
        abort(500, "Failed to parse image, please check your sector offset")

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
    
@route('/plugin/<name>/<image_id>/<offset>/<input_type>/<path_or_inode:path>')
def plugin(name, image_id, offset, input_type, path_or_inode):
    """Returns the iframe of the given plugin for the given file"""
    #Get file from database
    curr_file = helper.get_file(image_id, offset, input_type, path_or_inode)
    
    #Cache file
    file_cache_path = cache_file(curr_file)

    #Get mimetype and size
    actual_mimetype = helper.get_mimetype(file_cache_path)
    actual_size = os.path.getsize(file_cache_path)

    #Get Plugin
    plugin = plugin_manager.getPluginByName(str(name).lower())
    
    #Return plugins frame
    return plugin.plugin_object.get(curr_file, database, file_cache_path, actual_mimetype, actual_size, address, port, request.query)

@route('/directory/<image_id>/<offset>/<input_type>')
@route('/directory/<image_id>/<offset>/<input_type>/')
@route('/directory/<image_id>/<offset>/<input_type>/<path_or_inode:path>')
def directory(image_id, offset, input_type, path_or_inode="/"):
    """Returns a formatted directory listing for the given path"""
    #Get file from database
    curr_file = helper.get_file(image_id, offset, input_type, path_or_inode)
    
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

@route('/thumbnail/<image_id>/<offset>/<input_type>/')
@route('/thumbnail/<image_id>/<offset>/<input_type>/<path_or_inode:path>')
def thumbnail(image_id, offset, input_type, path_or_inode='/'):
    """Returns either an icon or thumbnail of the provided file"""
    #Get file from database
    curr_file = helper.get_file(image_id, offset, input_type, path_or_inode)
    
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

def icat(offset, image_path, metaaddress, output_file_path):
    """Returns the specified file using image file, meta or inode address, and outputfile"""
    #TODO: change to rb?
    out = open(output_file_path, 'wb')
    img = pytsk3.Img_Info(image_path, int(offset))
    fs = pytsk3.FS_Info(img)
    try:
        f = fs.open_meta(inode = int(metaaddress.split('-')[0]))
    except:
        logging.warn("Failed to cache file, most likey file is reallocated " + output_file_path)
        return
    file_offset = 0
    size = f.info.meta.size
    BUFF_SIZE = 1024 * 1024
    while file_offset < size:
        available_to_read = min(BUFF_SIZE, size - file_offset)
        data = f.read_random(file_offset, available_to_read)
        if not data: break
        file_offset += len(data)
        out.write(data)
    out.close()

def cache_file(curr_file, create_thumbnail=True):
    """Caches the provided file and returns the files cached directory"""
    if curr_file['file_type'] == 'directory':
        return
    
    file_cache_path = output_dir + 'files/' + curr_file['iid'] + '/' + curr_file['name']
    file_cache_dir = output_dir + 'files/' + curr_file['iid'] + '/'
    thumbnail_cache_path = output_dir + 'thumbnails/' + curr_file['iid'] + '/' + curr_file['name']
    thumbnail_cache_dir = output_dir + 'thumbnails/' + curr_file['iid'] + '/'
   
    #Makesure cache directories exist 
    if not os.path.isdir(thumbnail_cache_dir):
        os.makedirs(thumbnail_cache_dir)
    if not os.path.isdir(file_cache_dir):
        os.makedirs(file_cache_dir)

    #If file does not exist cat it to directory
    if not os.path.isfile(file_cache_path):
        icat(curr_file['offset'], curr_file['image_path'], curr_file['inode'], file_cache_path)

    #Uses extension to determine if it should create a thumbnail
    assumed_mimetype = helper.guess_mimetype(str(curr_file['ext']).lower())

    #If the file is an image create a thumbnail
    if assumed_mimetype.startswith('image') and create_thumbnail and not os.path.isfile(thumbnail_cache_path):
        try:
            image = Image.open(file_cache_path)
            image.thumbnail("42x42")
            image.save(thumbnail_cache_path)
        except IOError:
            logging.warn("Failed to create thumbnail for " + curr_file['name'] + " at cached path " + file_cache_path)
   
    return file_cache_path

def load_database(fs, image_id, offset, image_path, db, directory):
    for directory_entry in fs.open_dir(directory):
        name =  directory_entry.info.name.name.decode("utf8")
        if directory_entry.info.meta == None:
            file_type = ''
            inode = ''
            mod = ''
            acc = ''
            chg = ''
            cre = ''
            size = ''
            uid = ''
            gid = ''
        else:
            file_type = directory_entry.info.meta.type
            inode = str(directory_entry.info.meta.addr)
            mod = str(directory_entry.info.meta.mtime)
            acc = str(directory_entry.info.meta.atime)
            chg = str(directory_entry.info.meta.ctime)
            cre = str(directory_entry.info.meta.crtime)
            size = str(directory_entry.info.meta.size)
            uid = str(directory_entry.info.meta.uid)
            gid = str(directory_entry.info.meta.gid)
        
        dir_ref = image_id + "/" + offset + directory + name
        inode_ref = image_id + "/" + offset + "/" + inode
        ext = os.path.splitext(name)[1][1:] or ""

        if file_type == pytsk3.TSK_FS_META_TYPE_REG:
            file_type_str = 'regular'
        elif file_type == pytsk3.TSK_FS_META_TYPE_DIR:
            file_type_str = 'directory'
        elif file_type == pytsk3.TSK_FS_META_TYPE_LNK:
            file_type_str = 'link'
        else:
            file_type_str = str(file_type)
    
        db.insert(image_id + "/" + offset, dir_ref, inode_ref, image_id, offset, image_path, name, directory + name, ext, directory, file_type_str, inode, mod, acc, chg, cre, size, uid, gid)

        if file_type == pytsk3.TSK_FS_META_TYPE_DIR and name != "." and name != "..":
            try:
                load_database(fs, image_id, offset, image_path, db, directory + name + "/")
            except:
                logging.warn("[WARNING] - Failed to parse directory " + directory + name + "/")

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

def create_file(self, identifier, pid, iid, image_id, offset, image_path, name, path, ext, directory, file_type='regular', 
                inode='-1', mod='0', acc='0', chg='0', cre='0', size='0', uid='0', gid='0'):
    """Creates a dictionary file to be used with a plugin"""
    return dict([('id', identifier), ('pid', pid), ('iid', iid), ('image_id', image_id), ('offset', offset), ('image_path', image_path), 
                 ('name', name), ('path', path), ('ext', ext), ('dir', directory), ('file_type', file_type), ('inode', inode), 
                 ('mod', mod), ('acc', acc), ('chg', chg), ('cre', cre), ('size', size), ('uid', uid), ('gid', gid)])

if __name__=="__main__":
    main(sys.argv[1:])
