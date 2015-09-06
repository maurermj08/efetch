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

#TODO: Put cache in case folder 
#TODO: Update menu
#TODO: Add more basic configuration
#TODO: Add logging
#TODO: Updated Error handling
#TODO: Add case management page
#TODO: Add MetaDataTimeline ability
#TODO: Proper string escaping and filtering

global _debug
global default_image
global port
global default_case
global output_dir
global max_cache
global icon_dir
global curr_dir
global plugin_manager
global thumbnail_size
global max_download_size
global my_magic
global database

def main(argv):
    try: 
        opts, args = getopt.getopt(argv, "hp:i:c:o:s:dD:", ["help", "port=", "image=", "case=", "output=", "size=", "debug", "database="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    #logging.getLogger('yapsy').setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    global _debug
    global default_image
    global port
    global default_case
    global output_dir
    global max_cache
    global icon_dir
    global curr_dir
    global resource_dir
    global plugin_manager
    global thumbnail_size
    global max_download_size
    global my_magic
    global database

    my_magic = magic.Magic(flags=magic.MAGIC_MIME_TYPE)
    max_download_size = 100 #In MB #TODO: this should be configurable
    thumbnail_size = 128, 128 #TODO: This should be a configurable value
    _debug = 0 
    default_image = ""
    port = 8080
    default_case = str(int(time.time()))
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    output_dir = curr_dir + "/cache/"
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    icon_dir = curr_dir + "/icons/"
    resource_dir = curr_dir + "/resources/"
    thumbnail_dir = output_dir + "/thumbnails/"
    file_cache_dir = output_dir + "/files/"
    database_file = None
    
    if not os.path.isdir(icon_dir):
        print("ERROR: icon directory missing")
        sys.exit(2)
    
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-p", "--port"):
            port = arg
        elif opt in ("-i", "--image"):
            default_image = arg
        elif opt in ("-c", "--case"):
            default_case = arg
        elif opt in ("-o", "--output"):
            output_dir = arg
        elif opt in ("-s", "--size"):
            max_cache = arg    
        elif opt in ("-D", "--database"):
            database_file = arg
        elif opt == '-d':
            _debug = 1
        else:
            print("Unknown argument " + opt)
            usage()
            sys.exit(2)
    
    if not output_dir.endswith("/"):
        output_dir = output_dir + "/"
    if not os.path.isdir(output_dir):
        print("ERROR: output directory not found")
        sys.exit(2)
    if default_image and not os.path.isfile(default_image):
        print("ERROR: image file specified not found")
        sys.exit(2)    
    if database_file and not os.path.isfile(database_file):
        print("ERROR: database not found")
        sys.exit(2)

    if database_file != None:
        database = Base(database_file)
        if database.exists():
            database.open()
            database.create(mode='open')
        else:
            print("[ERROR] - Failed to open Database " + database_file)
            sys.exit(2)
    else:
        if _debug:
            print("[DEBUG] - Creating database")
        database = Base(default_case + '.pd1')
        image = pytsk3.Img_Info(url=default_image)
        file_system = pytsk3.FS_Info(image)
        if database.exists():
            database.open()
        else:
            database.create('case', 'image', 'offset', 'name', 'dir', 'file_type', 'inode', 'mod', 'acc', 'chg', 'cre', 'size', 'uid', 'gid')
        load_database(file_system, default_case, default_image, 0, database, "/")
        database.create_index('inode')
        database.create_index('name')
        database.create_index('dir')
        if _debug:
            print("[DEBUG] - Done creating database")
        database.commit()
        if _debug:
            print("[DEBUG] - Saved database")

    # Basic Plugin Management
    plugin_manager = PluginManager()
    plugin_manager.setPluginPlaces([curr_dir + "/plugins/"])
    plugin_manager.collectPlugins()    
    for plugin in plugin_manager.getAllPlugins():
        plugin_manager.activatePluginByName(plugin.name)

    run(host='localhost', port=port)
    
def icat(image, metaaddress, output_file, offset=0):
    """Returns the specified file using image file, meta or inode address, and outputfile"""
    out = open(output_file, 'wb')
    img = pytsk3.Img_Info(image)
    fs = pytsk3.FS_Info(img)
    f = fs.open_meta(inode = int(metaaddress.split('-')[0]))
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

def cache_file(is_image, thumbnails_dir, curr_file_dir, image, metaaddress, file_name, extension):
    """Caches the provided file"""
    if not os.path.isdir(thumbnails_dir):
        os.makedirs(thumbnails_dir)

    if not os.path.isdir(curr_file_dir):
        os.makedirs(curr_file_dir)

    if not os.path.isfile(curr_file_dir + file_name + "." + extension):
        icat(image, metaaddress, curr_file_dir + file_name + "." + extension)

    if is_image and not os.path.isfile(thumbnails_dir + metaaddress + "." + extension):
        try:
            image = Image.open(curr_file_dir + file_name + '.' + extension)
            image.thumbnail(thumbnail_size)
            image.save(thumbnails_dir + metaaddress + '.' + extension)
        except IOError:
            print("[WARN] Failed to parse image " + file_name + "." + extension)

@route('/analyze/<metaaddress>')
def analyze_file(metaaddress):
    extension = str(request.query.ext).replace(".","").lower() or "none"
    case = str(request.query.case).strip() or default_case
    image = str(request.query.image).strip() or default_image    
    file_type = str(request.query.type).strip().lower()
    file_name = str(request.query.filename).strip().lower() or "unknown"
    file_size = str(request.query.size).strip().lower() or "0"
    file_path = output_dir + case + '/' + 'files/' + metaaddress + '/' + file_name + "." + extension
    case_directory = output_dir + case + '/'
    thumbnails_dir = case_directory + 'thumbnails/'
    files_dir = case_directory + 'files/'
    curr_file_dir = files_dir + metaaddress + '/'
    mimetype = get_mime_type(extension)
    global plugin_manager
    plugins = []

    if _debug:
        print("[DEBUG] Analyzing file " + file_name)
        print("[DEBUG] Found the following plugins - " + str(plugin_manager.getAllPlugins()))
    
    plugins.append('<a href="http://localhost:' + port + '/directory?dir=' + database._inode[metaaddress.split('-')[0]][0]['dir'] + '" target="frame">Directory</a><br>')


    if int(file_size) / 1000000 <= max_download_size:
        if _debug:
            print("[DEBUG] File is smaller than max size")
        cache_file(False, thumbnails_dir, curr_file_dir, image, metaaddress, file_name, extension)
        actual_mimetype = my_magic.id_filename(file_path)
        actual_size = os.path.getsize(file_path)
        gets = "?file=" + file_path + "&mimetype=" + actual_mimetype + "&size=" + str(actual_size)
        for pop in reversed(range(1, 11)):
            for plugin in plugin_manager.getAllPlugins():    
                if plugin.plugin_object.popularity() == pop:
                    if _debug:
                        print("[DEBUG] Checking plugin " + plugin.plugin_object.display_name())
                    if plugin.plugin_object.check(actual_mimetype, actual_size):
                        if _debug:
                            print("[DEBUG] Adding!")
                        plugins.append('<a href="http://localhost:' + port + '/plugins/' + plugin.name + gets + '" target="frame">' + plugin.plugin_object.display_name() + '</a><br>')
    
    html = ""
    template = open(curr_dir + '/template.html', 'r')
    html = str(template.read())
    html = html.replace('<!-- Home -->', "http://localhost:" + port + "/directory?dir=" + database._inode[metaaddress.split('-')[0]][0]['dir'])
    html = html.replace('<!-- File -->', file_name) 
    html = html.replace('<!-- Mimetype -->', actual_mimetype)
    html = html.replace('<!-- Size -->', str(actual_size) + " Bytes")
    html = html.replace('<!-- Links -->', "\n".join(plugins))

    return html

@route('/plugins/<name>')
def plugin(name):
    """Returns the iframe of the given plugin for the given file"""
    file_path = str(request.query.file) or None
    mimetype = str(request.query.mimetype) or my_magic.id_filename(file_path)
    file_size = str(request.query.size) or os.path.getsize(file_path)

    if not file_path:
        return "ERROR: File required"

    curr_file = open(file_path, "rb")

    plugin = plugin_manager.getPluginByName(name)
    
    return plugin.plugin_object.get(curr_file, file_path, mimetype, file_size)

@route('/directory')
def directory():
    """Returns a directory listing for the given path"""
    dir_path = str(request.query.dir) or None

    if not dir_path:
        return "ERROR: Must pass a directory"

    listing = []
#(case, image, offset, directory + name, directory, str(file_type), inode, mod, acc, chg, cre, size, uid, gid)
    #TODO: Change localtime to case time, specifically what is supplied to sleuthkit
    for item in database._dir[dir_path]:        
        listing.append("    <tr>")  
        listing.append('        <td><img src="http://localhost:' + port + '/image/' + item['inode'] + '" alt="-" style="width:32px;height:32px;"></td>')
        listing.append('        <td><a href="http://localhost:' + port + '/analyze/' + item['inode'] + '" target="_top">' + os.path.basename(item['name']) + "</a></td>")
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

@route('/image/<metaaddress>')
def get_thumbnail(metaaddress):
    """Returns a thumbnail of the given file"""
    metaaddress = str(metaaddress).replace(',','')
    file_db = database._inode[metaaddress][0]
    extension = str(request.query.ext).replace(".","").lower() or os.path.splitext(file_db['name'])[1][1:]
    case = str(request.query.case).strip() or default_case
    image = str(request.query.image).strip() or default_image
    file_type = str(request.query.type).strip().lower() or None
    file_name = str(request.query.filename).strip().lower() or os.path.basename(os.path.splitext(file_db['name'])[0])
    case_directory = output_dir + case + '/'
    thumbnails_dir = case_directory + 'thumbnails/'
    files_dir = case_directory + 'files/'
    curr_file_dir = files_dir + metaaddress + '/'
    mime_type = ""

    if not file_type:
        if file_db['file_type'] == 'TSK_FS_META_TYPE_DIR':
            file_type = "directory"
        else:
            file_type = "regular"
    
    if file_type == "directory":
        return static_file("_folder.png", root=icon_dir, mimetype='image/png')

    if (extension == "jpg" or extension == "jpeg" or extension == "jfif" or extension == "jpe"):
        mime_type = 'image/jpeg'
    elif (extension == "png"):
        mime_type = 'image/png'
    elif (extension == "gif"):
        mime_type = 'image/gif'
    elif (extension == "bmp" or extension == "bm"):
        mime_type = 'image/bmp'
    elif (extension == "ico"):
        mime_type = 'image/xicon'
    elif (extension == "tif" or extension == "tiff"):
        mime_type = 'image/tiff'
    else:
        if not os.path.isfile(icon_dir + extension + ".png"):
            return static_file("_blank.png", root=icon_dir, mimetype='image/png')
        else:
            return static_file(extension + ".png", root=icon_dir, mimetype='image/png')

    cache_file(True, thumbnails_dir, curr_file_dir, image, metaaddress, file_name, extension)
    
    if os.path.isfile(case_directory + '/thumbnails/' + metaaddress + '.' + extension):
        return static_file(metaaddress + '.' + extension, root=thumbnails_dir, mimetype=mime_type)
    else:
        return static_file('_missing.png', root=icon_dir, mimetype='image/png')
        

@route('/file/<metaaddress>')
def get_file(metaaddress):
    extension = str(request.query.ext).replace(".","").lower() or "none"
    case = str(request.query.case).strip() or default_case
    image = str(request.query.image).strip() or default_image    
    file_type = str(request.query.type).strip().lower()
    file_name = str(request.query.filename).strip().lower() or "unknown"
    case_directory = output_dir + case + '/'
    thumbnails_dir = case_directory + 'thumbnails/'
    files_dir = case_directory + 'files/'
    curr_file_dir = files_dir + metaaddress + '/'
 
    if file_type == "directory":
        if not os.path.isdir(curr_file_dir):
            os.makedirs(curr_file_dir)
        extension = "txt"
        if not os.path.isfile(curr_file_dir + file_name + '.' + extension):
            fls(image, metaaddress, curr_file_dir + file_name + '.' + extension)
    
    mime_type = ""
    mime_type = get_mime_type(extension)
        
    cache_file(False, thumbnails_dir, curr_file_dir, image, metaaddress, file_name, extension)
    
    if mime_type: 
        return static_file(file_name + '.' + extension, root=case_directory + '/files/' + metaaddress + '/', mimetype=mime_type)
    else:
        return static_file(file_name + '.' + extension, root=case_directory + '/files/' + metaaddress + '/', download=True)

@route('/resource/<name>')
def get_resource(name):
    if not name:
        return
    name = str(name)
    if '/' in name or name == '.' or name == '..':
        return
    return static_file(name, root=resource_dir, mimetype='image/jpg')

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

def load_database(fs, case, image, offset, db, directory):
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
        
        db.insert(case, image, offset, directory + name, directory, str(file_type), inode, mod, acc, chg, cre, size, uid, gid)

        if file_type == pytsk3.TSK_FS_META_TYPE_DIR and name != "." and name != "..":
            try:
                load_database(fs, case, image, offset, db, directory + name + "/")
            except:
                print("[WARNING] - Failed to parse directory " + directory + name + "/")

def usage():
    print("usage: evidence_rest_server.py [-h] [-p PORT] [-i IMAGE] [-c CASE] [-o DIR ] [-s SIZE] [-d] [-D database]")
    print("")
    print("evidence_rest_server is a simple webserver that can return files and thumbnails from an image.")
    print("!!!WARNING!!! there are major known security issues if this is run as root and externally facing!")
    print("")
    print("optional arguments:")
    print("  -h, --help        shows this help message and exits")
    print("  -p, --port         sets the port this server runs on, defaults to 8080")
    print("  -i, --image        default evidence IMAGE to use, if not specified in the request")
    print("  -c, --case        default case to use, if not specified in the request")
    print("  -o, --output        directory to store output files")
    print("  -s, --size        the max size of cache storage, defaults to 1GB [NOT IMPLEMENTED]")
    print("  -d, --debug        displays debug output")
    print("  -D, --database     use an existing database file")
    print("")

if __name__=="__main__":
    main(sys.argv[1:])
