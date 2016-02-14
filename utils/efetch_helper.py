#!/usr/bin/python
import logging
import magic
import os
from bottle import abort
from db_util import DBUtil
from PIL import Image
from yapsy.PluginManager import PluginManager

class EfetchHelper(object):
    """This class provides helper methods to be used in Efetch and its plugins"""

    def __init__(self, curr_directory, output_directory, upload_directory,
            max_file_size, es_url=None):
        """Initializes the Efetch Helper"""
        _pymagic = None
        _my_magic = None

        self.max_file_size = max_file_size

        #Setup directory references
        self.curr_dir = curr_directory
        self.output_dir = output_directory
        self.upload_dir = upload_directory
        self.resource_dir = self.curr_dir + '/resources/'
        self.icon_dir = self.curr_dir + '/icons/'
        if not os.path.isdir(self.icon_dir):
            logging.error('Could not find icon directory ' + self.icon_dir)
            sys.exit(2)

        #Elastic Search DB setup
        if es_url:
            self.db_util = DBUtil()
        else:
            self.db_util = DBUtil(es_url)
        
        #Plugin Manager Setup
        self.plugin_manager = PluginManager()
        self.plugin_manager.setPluginPlaces([self.curr_dir + '/plugins/'])
        self.reload_plugins()

        #Determine which magic lib to use
        try:
            self._my_magic = magic.Magic(mime=True)
            self._pymagic = True
        except:
            self._my_magic = magic.Magic(flags=magic.MAGIC_MIME_TYPE)
            self._pymagic = False

    def reload_plugins(self):
        """Reloads all Yapsy plugins"""
        self.plugin_manager.collectPlugins()
        for plugin in self.plugin_manager.getAllPlugins():
            self.plugin_manager.activatePluginByName(plugin.name)

    def get_request_value(self, request, variable_name, default=None):
        """Gets the value of a variable in either a GET or POST request"""
        if variable_name in request.query:
            return request.query[variable_name]
        elif request.forms.get(variable_name):
            return request.forms.get(variable_name)
        return default

    def get_mimetype(self, file_path):
        """Returns the mimetype for the given file"""
        if self._pymagic:
            return self._my_magic.from_file(file_path)
        else:
            return self._my_magic.id_filename(file_path)

    def cache_file(self, curr_file, create_thumbnail=True):
        """Caches the provided file and returns the files cached directory"""
        if curr_file['meta_type'] != 'File':
            return None
        if int(curr_file['file_size'][0]) > self.max_file_size:
            return None

        #TODO: Not everything will have an iid... so need to figure that out
        file_cache_path = self.output_dir + 'files/' + curr_file['iid'] + '/' + curr_file['name']
        file_cache_dir = self.output_dir + 'files/' + curr_file['iid'] + '/'
        thumbnail_cache_path = self.output_dir + 'thumbnails/' + curr_file['iid'] + '/' + \
                curr_file['name']
        thumbnail_cache_dir = self.output_dir + 'thumbnails/' + curr_file['iid'] + '/'

        #Makesure cache directories exist 
        if not os.path.isdir(thumbnail_cache_dir):
            os.makedirs(thumbnail_cache_dir)
        if not os.path.isdir(file_cache_dir):
            os.makedirs(file_cache_dir)

        #If file does not exist cat it to directory
        if not os.path.isfile(file_cache_path):
            self.plugin_manager.getPluginByName(curr_file['driver']).plugin_object.icat(curr_file, 
                    file_cache_path)

        #Uses extension to determine if it should create a thumbnail
        assumed_mimetype = self.guess_mimetype(str(curr_file['ext']).lower())

        #If the file is an image create a thumbnail
        if assumed_mimetype.startswith('image') and create_thumbnail and \
                not os.path.isfile(thumbnail_cache_path):
            try:
                image = Image.open(file_cache_path)
                image.thumbnail('42x42')
                image.save(thumbnail_cache_path)
            except IOError:
                logging.warn('Failed to create thumbnail for ' + curr_file['name'] + \
                        ' at cached path ' + file_cache_path)

        return file_cache_path

    def guess_mimetype(self, extension):
        """Returns the assumed mimetype based on the extension"""
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
            'cdf'    : 'application/x-cdf',
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
            'xls'    : 'application/excel',
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
            return '' 
