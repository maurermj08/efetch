from bottle import route, run, request, static_file
import subprocess
import os
import sys
import getopt
import time
import pytsk3
from PIL import Image

global _debug
global default_image
global port
global default_case
global output_dir
global max_cache

def main(argv):
	try: 
		opts, args = getopt.getopt(argv, "hp:i:c:o:s:d", ["help", "port=", "image=", "case=", "output=", "size=", "debug"])
	except getopt.GetoptError:
		usage()
		sys.exit(2)

	global _debug
	global default_image
	global port
	global default_case
	global output_dir
	global max_cache

	_debug = 0
	default_image = ""
	port = 8080
	default_case = int(time.time())
	output_dir = ""

	for opt, arg in opts:
		if opt in ("-h", "--help"):
			usage()
			sys.exit()
		elif opt == '-d':
			_debug = 1
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
		else:
			print "Unknown argument " + opt
			usage()
			sys.exit(2)
	
	if not output_dir:
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
	
	run(host='localhost', port=port)
	
def usage():
	print "usage: evidence_rest_server.py [-h] [-p PORT] [-i IMAGE] [-c CASE] [-o DIR ] [-s SIZE] [-d]"
	print ""
	print "evidence_rest_server is a simple webserver that can return files and thumbnails from an image."
	print "!!!WARNING!!! there are major known security issues if this is run as root and externally facing!"
	print ""
	print "required arguments:"
	print "  -o, --output		directory to store output files"
	print "optional arguments:"
	print "  -h, --help		shows this help message and exits"
	print "  -p, --port 		sets the port this server runs on, defaults to 8080"
	print "  -i, --image		default evidence IMAGE to use, if not specified in the request"
	print "  -c, --case		default case to use, if not specified in the request"
	print "  -s, --size		the max size of cache storage, defaults to 1GB [NOT IMPLEMENTED]"
	print "  -d, --debug		displays debug output"
	print 

def icat(image, metaaddress, output_file):
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

def fls(image, metaaddress, output_file):
	out = open(output_file, 'w')
	img = pytsk3.Img_Info(image)
	fs = pytsk3.FS_Info(img)
	directory = fs.open_dir(inode = int(metaaddress.split('-')[0]))
	for entry in directory:
		out.write(entry.info.name.name + "\n")
	out.close()

def load_files(is_image, thumbnails_dir, curr_file_dir, image, metaaddress, file_name, extension):
	thumbnail_size = 128, 128
	
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
			print "[WARN] Failed to parse image " + file_name + "." + extension

@route('/image/<metaaddress>')
def get_image(metaaddress):
	metaaddress = str(metaaddress).replace(',','')
	extension = str(request.query.ext).replace(".","").lower() or "_blank"
	case = str(request.query.case).strip() or default_case
	image = str(request.query.image).strip() or default_image
	file_type = str(request.query.type).strip().lower() or "regular"
	file_name = str(request.query.filename).strip().lower() or ""
	case_directory = output_dir + case + '/'
	thumbnails_dir = case_directory + 'thumbnails/'
	files_dir = case_directory + 'files/'
	curr_file_dir = files_dir + metaaddress + '/'
	mime_type = ""

	if not file_name:
		full_name = os.popen("basename \"`ffind " + image + " " + metaaddress.split("-")[0] + "`\"" ).read()
		parts = full_name.split(".",1)
		if len(parts) > 1:
			file_name = parts[0]
			extension = str(parts[1]).strip().lower()
			print extension

	if file_type == "directory":
    		return static_file("_folder.png", root='/cases/icons/', mimetype='image/png')

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
		if not os.path.isfile('/cases/icons/' + extension + ".png"):
    			return static_file("_blank.png", root='/cases/icons/', mimetype='image/png')
		else:
			return static_file(extension + ".png", root='/cases/icons/', mimetype='image/png')

	load_files(True, thumbnails_dir, curr_file_dir, image, metaaddress, file_name, extension)
	
	if os.path.isfile('/cases/' + case  + '/thumbnails/' + metaaddress + '.' + extension):
		return static_file(metaaddress + '.' + extension, root='/cases/' + case  + '/thumbnails/', mimetype=mime_type)
	else:
		return static_file('_missing.png', root='/cases/icons/', mimetype='image/png')
		

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
		
	load_files(False, thumbnails_dir, curr_file_dir, image, metaaddress, file_name, extension)
	
	if mime_type: 
    		return static_file(file_name + '.' + extension, root='/cases/' + case  + '/files/' + metaaddress + '/', mimetype=mime_type)
	else:
    		return static_file(file_name + '.' + extension, root='/cases/' + case  + '/files/' + metaaddress + '/', download=True)


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

	
if __name__=="__main__":
	main(sys.argv[1:])
