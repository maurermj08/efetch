from bottle import route, run, request, static_file
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
from yapsy.PluginManager import PluginManager
from bottle import abort

#TODO: Add case management page
#TODO: Proper string escaping and filtering

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
    global plugin_manager
    global max_download_size
    global my_magic
    global database

    #Instantiate Globals
    my_magic = magic.Magic(flags=magic.MAGIC_MIME_TYPE)
    
    #Default Values
    max_download_size = 100 #In MegaBytes
    _debug = 0 
    address = "localhost"
    port = str(8080)
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    output_dir = curr_dir + "/cache/"
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    icon_dir = curr_dir + "/icons/"
    database_file = None
    logging.basicConfig(level=logging.INFO)
    
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
            _debug = 1
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
            print("[ERROR] - Failed to open Database " + database_file)
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
        if _debug:
            print("[DEBUG] - Saved database")

    #TODO MOVE TO analyze
    # Basic Plugin Management
    plugin_manager = PluginManager()
    plugin_manager.setPluginPlaces([curr_dir + "/plugins/"])
    plugin_manager.collectPlugins()    
    for plugin in plugin_manager.getAllPlugins():
        plugin_manager.activatePluginByName(plugin.name)

    run(host=address, port=port)

def get_file(image_id, offset, input_type, path_or_inode, abort_on_error=True):
    """Returns the file object for the given file in the database"""
    if path_or_inode.endswith('/'):
        path_or_inode = path_or_inode[:-1]
    #Check if image and offset are in database
    if not database._id[image_id + '/' + offset]:
        logging.error("Could not find image with provided id and offset " + image_id + "/" + offset)
        if abort_on_error:
            abort(400, "No image with id " + image_id + " and offset " + offset)
        else:
            return
    
    #Get file from either path or inode
    if str(input_type).lower().strip() == 'p':
        curr_file = database._pid[image_id + '/' + offset + '/' + path_or_inode]
    elif str(input_type).lower().strip() == 'i':
        curr_file = database._iid[image_id + '/' + offset + '/' + path_or_inode]
    else:
        logging.error("Unsupported input type '" + input_type + "' provided")
        if abort_on_error:
            abort(400, "Only supports input types of 'p' for path or 'i' for inode\nFormat is '/analyze/<image_id>/<offset>/<type[p or i]>/<fullpath or inode>'")
        else:
            return
    if not curr_file:
        logging.error("Could not find file. Image='" + image_id + "' Offset='" + offset + "' Type='" + input_type + "' Path or Inode='" + path_or_inode + "'")
        if abort_on_error:
            abort(404, "Could not find file in provided image.")
        else:
            return

    return curr_file[0]

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
        database.insert(image_id + "/" + offset, image_id + '/' + offset + '/', image_id + '/' + offset + '/-1', image_id, offset, image_path, '/', '', '', '', 'TSK_FS_META_TYPE_DIR', -1, 0, 0, 0, 0, 0, 0, 0)
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
    curr_file = get_file(image_id, offset, input_type, path_or_inode)

    #Caching variables
    file_cache_path = output_dir + 'files/' + curr_file['iid'] + '/' + curr_file['name']
    file_cache_dir = output_dir + 'files/' + curr_file['iid'] + '/'
    thumbnail_cache_path = output_dir + 'thumbnails/' + curr_file['iid'] + '/' + curr_file['name']
    thumbnail_cache_dir = output_dir + 'thumbnails/' + curr_file['iid'] + '/'

    logging.debug("Analyzing file " + curr_file['name'])
    logging.debug("Found the following plugins - " + str(plugin_manager.getAllPlugins()))
    
    #Add Directoy link
    plugins = []
    plugins.append('<a href="http://' + address + ':' + port + '/directory/' + curr_file['image_id'] + '/' + curr_file['offset']  + '/p' + curr_file['path'] + '" target="frame">Directory</a><br>')

    #If file is less than max download (cache) size, cache it and analyze it
    if curr_file['file_type'] != 'TSK_FS_META_TYPE_DIR' and int(curr_file['size']) / 1000000 <= max_download_size:
        cache_file(False, thumbnail_cache_dir, file_cache_dir, curr_file['image_path'], curr_file['offset'], curr_file['inode'], curr_file['name'], curr_file['ext'])
        actual_mimetype = my_magic.id_filename(file_cache_path)
        actual_size = os.path.getsize(file_cache_path)
        #Order Plugins by populatiry from highest to lowest
        for pop in reversed(range(1, 11)):
            for plugin in plugin_manager.getAllPlugins():    
                if plugin.plugin_object.popularity() == pop:
                    #Check if plugin applies to curr file
                    if plugin.plugin_object.check(actual_mimetype, actual_size):
                        logging.debug("Check matched, adding plugin " + plugin.plugin_object.display_name())
                        plugins.append('<a href="http://' + address + ':' + port + '/plugin/' + plugin.name + '/' + curr_file['image_id'] + '/' + curr_file['offset'] + '/p' + curr_file['path'] + '" target="frame">' + plugin.plugin_object.display_name() + '</a><br>')
                    else:
                        logging.debug("Check did not match, NOT adding plugin " + plugin.plugin_object.display_name())

    #Modifies HTML page
    html = ""
    template = open(curr_dir + '/template.html', 'r')
    html = str(template.read())
    html = html.replace('<!-- Home -->', "http://" + address + ":" + port + "/directory/" + curr_file['image_id'] + '/' + curr_file['offset']  + '/p' + curr_file['path'])
    if curr_file['file_type'] == 'TSK_FS_META_TYPE_DIR':
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
    curr_file = get_file(image_id, offset, input_type, path_or_inode)
    
    #Caching variables
    file_cache_path = output_dir + 'files/' + curr_file['iid'] + '/' + curr_file['name']
    file_cache_dir = output_dir + 'files/' + curr_file['iid'] + '/'
    thumbnail_cache_path = output_dir + 'thumbnails/' + curr_file['iid'] + '/' + curr_file['name']
    thumbnail_cache_dir = output_dir + 'thumbnails/' + curr_file['iid'] + '/'

    #Check if file has been cached, if not cache it
    if not os.path.isfile(file_cache_path):
        thumbnail_cache_path = output_dir + 'thumbnails/' + curr_file['iid'] + '/' + curr_file['name']
        cache_file(False, thumbnail_cache_dir, file_cache_dir, curr_file['image_path'], curr_file['offset'], curr_file['inode'], curr_file['name'], curr_file['ext'])

    #Get mimetype and size
    actual_mimetype = my_magic.id_filename(file_cache_path)
    actual_size = os.path.getsize(file_cache_path)

    #Open file
    curr_file = open(file_cache_path, "rb")

    #Get Plugin
    plugin = plugin_manager.getPluginByName(name)
    
    #Return plugins frame
    return plugin.plugin_object.get(curr_file, file_cache_path, actual_mimetype, actual_size)

@route('/directory/<image_id>/<offset>/<input_type>')
@route('/directory/<image_id>/<offset>/<input_type>/')
@route('/directory/<image_id>/<offset>/<input_type>/<path_or_inode:path>')
def directory(image_id, offset, input_type, path_or_inode="/"):
    """Returns a formatted directory listing for the given path"""
    #Get file from database
    curr_file = get_file(image_id, offset, input_type, path_or_inode)
    
    #Caching variables
    file_cache_path = output_dir + 'files/' + curr_file['iid'] + '/' + curr_file['name']
    file_cache_dir = output_dir + 'files/' + curr_file['iid'] + '/'
    thumbnail_cache_path = output_dir + 'thumbnails/' + curr_file['iid'] + '/' + curr_file['name']
    thumbnail_cache_dir = output_dir + 'thumbnails/' + curr_file['iid'] + '/'

    #Check if file has been cached, if not cache it
    if curr_file['file_type'] != 'TSK_FS_META_TYPE_DIR' and not os.path.isfile(file_cache_path):
        thumbnail_cache_path = output_dir + 'thumbnails/' + curr_file['iid'] + '/' + curr_file['name']
        cache_file(False, thumbnail_cache_dir, file_cache_dir, curr_file['image_path'], curr_file['offset'], curr_file['inode'], curr_file['name'], curr_file['ext'])
   
    #If path is a folder just set the view to it, if not use the files parent folder
    if curr_file['file_type'] == 'TSK_FS_META_TYPE_DIR':
        curr_folder = curr_file['path'] + "/"
    else:
        curr_folder = curr_file['dir']

    listing = []
    #TODO: Change localtime to case time, specifically what is supplied to sleuthkit
    for item in database._dir[curr_folder]:        
        listing.append("    <tr>")  
        listing.append('        <td><img src="http://' + address + ':' + port + '/thumbnail/' + item['image_id'] + '/' + item['offset'] + '/p' + item['path'] + '" alt="-" style="width:32px;height:32px;"></td>')
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

@route('/file/<image_id>/<offset>/<input_type>/<path_or_inode:path>')
def files(image_id, offset, input_type, path_or_inode):
    """Returns the given file"""
    #Get file from database
    curr_file = get_file(image_id, offset, input_type, path_or_inode, False)
    
    #Caching variables
    file_cache_path = output_dir + 'files/' + curr_file['iid'] + '/' + curr_file['name']
    file_cache_dir = output_dir + 'files/' + curr_file['iid'] + '/'

    #Check if file has been cached, if not cache it
    if not os.path.isfile(file_cache_path):
        thumbnail_cache_dir = output_dir + 'thumbnails/' + curr_file['iid'] + '/'
        cache_file(False, thumbnail_cache_dir, file_cache_dir, curr_file['image_path'], curr_file['offset'], curr_file['inode'], curr_file['name'], curr_file['ext'])
    
    actual_mimetype = my_magic.id_filename(file_cache_path)
    
    return static_file(curr_file['name'], root=file_cache_dir, mimetype=actual_mimetype)

@route('/thumbnail/<image_id>/<offset>/<input_type>/<path_or_inode:path>')
def thumbnail(image_id, offset, input_type, path_or_inode):
    """Returns either an icon or thumbnail of the provided file"""
    #Get file from database
    curr_file = get_file(image_id, offset, input_type, path_or_inode)
    
    #If it is folder just return the folder icon
    if curr_file['file_type'] == 'TSK_FS_META_TYPE_DIR' or str(curr_file['name']).strip() == "." or str(curr_file['name']).strip() == "..":
        return static_file("_folder.png", root=icon_dir, mimetype='image/png')

    #Uses extension to determine if it should create a thumbnail
    assumed_mimetype = get_mime_type(curr_file['ext'])

    #If the file is an image create a thumbnail
    if assumed_mimetype.startswith('image'):
        #Caching variables
        file_cache_path = output_dir + 'files/' + curr_file['iid'] + '/' + curr_file['name']
        file_cache_dir = output_dir + 'files/' + curr_file['iid'] + '/'
    
        #Check if file has been cached, if not cache it
        if not os.path.isfile(file_cache_path):
            thumbnail_cache_path = output_dir + 'thumbnails/' + curr_file['iid'] + '/' + curr_file['name']
            thumbnail_cache_dir = output_dir + 'thumbnails/' + curr_file['iid'] + '/'
            cache_file(True, thumbnail_cache_path, file_cache_path, curr_file['image_path'], curr_file['offset'], curr_file['inode'], curr_file['name'], curr_file['ext'])
    
        #TODO: If this is always a jpeg just state it, should save some time
        thumbnail_mimetype = my_magic.id_filename(thumbnail_cache_path)
        
        if os.path.isfile(thumbnail_cache_dir):
            return static_file(curr_file['name'], root=thumbnail_cache_dir, mimetype=actual_mimetype)
        else:
            return static_file('_missing.png', root=icon_dir, mimetype='image/png')
    #If file is not an image return the icon associated with the files extension
    else:
        if not os.path.isfile(icon_dir + curr_file['ext'] + ".png"):
            return static_file("_blank.png", root=icon_dir, mimetype='image/png')
        else:
            return static_file(curr_file['ext'] + ".png", root=icon_dir, mimetype='image/png')

def icat(offset, image_path, metaaddress, output_file):
    """Returns the specified file using image file, meta or inode address, and outputfile"""
    out = open(output_file, 'wb')
    #TODO ADD OFFSET
    img = pytsk3.Img_Info(image_path)
    fs = pytsk3.FS_Info(img)
    f = fs.open_meta(inode = int(metaaddress.split('-')[0]))
    #TODO RENAME VARIABLE
    offset = 0
    size = f.info.meta.size
    BUFF_SIZE = 1024 * 1024
    while offset < size:
        available_to_read = min(BUFF_SIZE, size - offset)
        data = f.read_random(offset, available_to_read)
        if not data: break
        offset += len(data)
        out.write(data)
    out.close()

def cache_file(is_image, thumbnails_dir, curr_file_dir, image_path, offset, metaaddress, file_name, extension):
    """Caches the provided file"""
    if not os.path.isdir(thumbnails_dir):
        os.makedirs(thumbnails_dir)

    if not os.path.isdir(curr_file_dir):
        os.makedirs(curr_file_dir)

    if not os.path.isfile(curr_file_dir + file_name):
        icat(offset, image_path, metaaddress, curr_file_dir + file_name)

    if is_image and not os.path.isfile(thumbnails_dir + file_name):
        try:
            image = Image.open(curr_file_dir + file_name)
            image.thumbnail(thumbnail_size)
            image.save(thumbnails_dir + file_name)
        except IOError:
            logging.warn("[WARN] Failed to parse image " + file_name)

def get_mime_type(extension):
    types_map = {
        'a'      : 'application/octet-stream',
        'ai'     : 'application/postscript',
        'aif'    : 'audio/x-aiff',
        'aifc'   : 'audio/x-aiff',
        'aiff'   : 'audio/x-aiff',
        'au'     : 'audio/basic',
        'avi'    : 'video/x-msvideo',
        'bat'    : 'text/plain',
        'bcpio'  : 'application/x-bcpio',
        'bin'    : 'application/octet-stream',
        'bmp'    : 'image/x-ms-bmp',
        'c'      : 'text/plain',
        # Duplicates :(
        'cdf'    : 'application/x-cdf',
        'cdf'    : 'application/x-netcdf',
        'cpio'   : 'application/x-cpio',
        'csh'    : 'application/x-csh',
        'css'    : 'text/css',
        'dll'    : 'application/octet-stream',
        'doc'    : 'application/msword',
        'dot'    : 'application/msword',
        'dvi'    : 'application/x-dvi',
        'eml'    : 'message/rfc822',
        'eps'    : 'application/postscript',
        'etx'    : 'text/x-setext',
        'exe'    : 'application/octet-stream',
        'gif'    : 'image/gif',
        'gtar'   : 'application/x-gtar',
        'h'      : 'text/plain',
        'hdf'    : 'application/x-hdf',
        'htm'    : 'text/html',
        'html'   : 'text/html',
        'ico'    : 'image/vnd.microsoft.icon',
        'ief'    : 'image/ief',
        'jpe'    : 'image/jpeg',
        'jpeg'   : 'image/jpeg',
        'jpg'    : 'image/jpeg',
        'js'     : 'application/javascript',
        'ksh'    : 'text/plain',
        'latex'  : 'application/x-latex',
        'm1v'    : 'video/mpeg',
        'man'    : 'application/x-troff-man',
        'me'     : 'application/x-troff-me',
        'mht'    : 'message/rfc822',
        'mhtml'  : 'message/rfc822',
        'mif'    : 'application/x-mif',
        'mov'    : 'video/quicktime',
        'movie'  : 'video/x-sgi-movie',
        'mp2'    : 'audio/mpeg',
        'mp3'    : 'audio/mpeg',
        'mp4'    : 'video/mp4',
        'mpa'    : 'video/mpeg',
        'mpe'    : 'video/mpeg',
        'mpeg'   : 'video/mpeg',
        'mpg'    : 'video/mpeg',
        'ms'     : 'application/x-troff-ms',
        'nc'     : 'application/x-netcdf',
        'nws'    : 'message/rfc822',
        'o'      : 'application/octet-stream',
        'obj'    : 'application/octet-stream',
        'oda'    : 'application/oda',
        'p12'    : 'application/x-pkcs12',
        'p7c'    : 'application/pkcs7-mime',
        'pbm'    : 'image/x-portable-bitmap',
        'pdf'    : 'application/pdf',
        'pfx'    : 'application/x-pkcs12',
        'pgm'    : 'image/x-portable-graymap',
        'pl'     : 'text/plain',
        'png'    : 'image/png',
        'pnm'    : 'image/x-portable-anymap',
        'pot'    : 'application/vnd.ms-powerpoint',
        'ppa'    : 'application/vnd.ms-powerpoint',
        'ppm'    : 'image/x-portable-pixmap',
        'pps'    : 'application/vnd.ms-powerpoint',
        'ppt'    : 'application/vnd.ms-powerpoint',
        'ps'     : 'application/postscript',
        'pwz'    : 'application/vnd.ms-powerpoint',
        'py'     : 'text/x-python',
        'pyc'    : 'application/x-python-code',
        'pyo'    : 'application/x-python-code',
        'qt'     : 'video/quicktime',
        'ra'     : 'audio/x-pn-realaudio',
        'ram'    : 'application/x-pn-realaudio',
        'ras'    : 'image/x-cmu-raster',
        'rdf'    : 'application/xml',
        'rgb'    : 'image/x-rgb',
        'roff'   : 'application/x-troff',
        'rtx'    : 'text/richtext',
        'sgm'    : 'text/x-sgml',
        'sgml'   : 'text/x-sgml',
        'sh'     : 'application/x-sh',
        'shar'   : 'application/x-shar',
        'snd'    : 'audio/basic',
        'so'     : 'application/octet-stream',
        'src'    : 'application/x-wais-source',
        'sv4cpio': 'application/x-sv4cpio',
        'sv4crc' : 'application/x-sv4crc',
        'swf'    : 'application/x-shockwave-flash',
        't'      : 'application/x-troff',
        'tar'    : 'application/x-tar',
        'tcl'    : 'application/x-tcl',
        'tex'    : 'application/x-tex',
        'texi'   : 'application/x-texinfo',
        'texinfo': 'application/x-texinfo',
        'tif'    : 'image/tiff',
        'tiff'   : 'image/tiff',
        'tr'     : 'application/x-troff',
        'tsv'    : 'text/tab-separated-values',
        'txt'    : 'text/plain',
        'ustar'  : 'application/x-ustar',
        'vcf'    : 'text/x-vcard',
        'wav'    : 'audio/x-wav',
        'wiz'    : 'application/msword',
        'wsdl'   : 'application/xml',
        'xbm'    : 'image/x-xbitmap',
        'xlb'    : 'application/vnd.ms-excel',
        # Duplicates :(
        'xls'    : 'application/excel',
        'xls'    : 'application/vnd.ms-excel',
        'xml'    : 'text/xml',
        'xpdl'   : 'application/xml',
        'xpm'    : 'image/x-xpixmap',
        'xsl'    : 'application/xml',
        'xwd'    : 'image/x-xwindowdump',
        'zip'    : 'application/zip',
    }
    
    if extension in types_map:
        return types_map[extension]
    else:
        return "" 

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

        db.insert(image_id + "/" + offset, dir_ref, inode_ref, image_id, offset, image_path, name, directory + name, ext, directory, str(file_type), inode, mod, acc, chg, cre, size, uid, gid)

        if file_type == pytsk3.TSK_FS_META_TYPE_DIR and name != "." and name != "..":
            try:
                load_database(fs, image_id, offset, image_path, db, directory + name + "/")
            except:
                logging.warn("[WARNING] - Failed to parse directory " + directory + name + "/")

def usage():
    print("usage: efetch.py [-h] [-p PORT] [-o DIR ] [-s SIZE] [-d] [-D database] [-m maxfilesize")
    print("")
    print("efetch is a simple webserver that can return files and thumbnails from an image.")
    print("!!!WARNING!!! there are major known security issues if this is run as root and externally facing!")
    print("")
    print("optional arguments:")
    print("  -h, --help         shows this help message and exits")
    print("  -p, --port         sets the port this server runs on, defaults to 8080")
    print("  -o, --output       directory to store output files")
    print("  -s, --size         the max size of cache storage, defaults to 1GB [NOT IMPLEMENTED]")
    print("  -d, --debug        displays debug output")
    print("  -D, --database     use an existing database file")
    print("  -m, --maxfilesize  max file size to download when caching files")
    print("")

if __name__=="__main__":
    main(sys.argv[1:])
