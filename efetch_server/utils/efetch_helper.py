# Copyright 2016 Michael J Maurer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import datetime
import hashlib
import logging
import magic
import os
import pytsk3
import time
import threading
import traceback
from bottle import abort
from db_util import DBUtil
from plugin_manager import EfetchPluginManager
from poll import Poll
from dfvfs.resolver import resolver
from dfvfs.serializer.json_serializer import JsonPathSpecSerializer
from PIL import Image
from urllib import urlencode


class EfetchHelper(object):
    """This class provides helper methods to be used in Efetch and its plugins"""


    def __init__(self, curr_directory, output_directory, max_file_size, plugins_file, es_url):
        """Initializes the Efetch Helper"""
        self._cache_lock = threading.Lock()
        self._mime_lock = threading.Lock()
        self._read_lock = threading.Lock()
        self._caching = []
        self._reading = {}
        self.max_file_size = max_file_size

        # Setup directory references
        self.curr_dir = curr_directory
        self.output_dir = output_directory
        self.resource_dir = self.curr_dir + os.path.sep + u'resources' + os.path.sep
        self.icon_dir = self.resource_dir + u'icons' + os.path.sep
        if not os.path.isdir(self.icon_dir):
            logging.error(u'Could not find icon directory ' + self.icon_dir)

        # Create plugin manager and begin polling for changes to plugins
        self.plugin_manager = EfetchPluginManager(plugins_file, self.curr_dir)
        self.poll = Poll(self.plugin_manager)
        self.poll.start()

        # Elastic Search DB setup
        if es_url:
            self.db_util = DBUtil()
        else:
            self.db_util = DBUtil(es_url)

        # Determine which magic lib to use
        try:
            self._my_magic = magic.Magic(mime=True)
            self._pymagic = True
        except:
            self._my_magic = magic.Magic(flags=magic.MAGIC_MIME_TYPE)
            self._pymagic = False


    def get_request_value(self, request, variable_name, default=None):
        """Gets the value of a variable in either a GET or POST request"""
        if variable_name in request.query:
            return request.query[variable_name]
        elif request.forms.get(variable_name):
            return request.forms.get(variable_name)
        return default

    def get_query_string(self, request, default_query=''):
        """Returns the query string of the given request"""
        if request.query_string:
            return "?" + request.query_string
        else:
            return default_query

    def get_query(self, request):
        """Gets the Kibana Query from the request"""
        return self.db_util.get_query(self.get_request_value(request, '_a', '()'))

    def get_theme(self, request):
        """Gets the Kibana Theme from the request"""
        return self.db_util.get_theme(self.get_request_value(request, '_a', '()'))

    def get_filters(self, request, must=[], must_not=[]):
        """Gets the Kibana Filter from the request"""
        return self.db_util.get_filters(self.get_request_value(request, '_a', '()'),
                                        self.get_request_value(request, '_g', '()'), must, must_not)

    def get_mimetype(self, encoded_pathspec, file_path, repeat=2):
        """Returns the mimetype for the given file"""

        if encoded_pathspec in self._caching:
            with self._cache_lock:
                pass

        try:
            with self._mime_lock:
                if self._pymagic:
                    return self._my_magic.from_file(file_path)
                else:
                    return self._my_magic.id_filename(file_path)
        except:
            if repeat > 0:
                logging.warn('Failed to get the mimetype for "%s" attempting again in 100ms', file_path)
                time.sleep(0.100)
                self.get_mimetype(encoded_pathspec, file_path, repeat - 1)
            else:
                return False
            traceback.print_stack()
            logging.warn('Failed to get the mimetype for "%s"', file_path)

    def _decode_pathspec(self, encoded_pathspec):
        """Returns a Path Spec object from an encoded path spec, causes a 400 abort if the decode fails"""
        if not encoded_pathspec:
            logging.warn('Path Spec required but none found')
            abort(400, 'Expected an encoded Path Spec, but none found')

        try:
            return JsonPathSpecSerializer.ReadSerialized(encoded_pathspec)
        except Exception as e:
            logging.warn('Failed to decode pathspec')
            logging.debug(encoded_pathspec)
            logging.debug(e.message)
            logging.debug(traceback.format_exc())
            abort(400, 'Failed to decode path spec')

    def _get_file_entry(self, encoded_pathspec):
        """Returns an open File Entry object of the given path spec, causes a 404 abort if the file is not found"""
        try:
            with self._read_lock:
                return resolver.Resolver.OpenFileEntry(self._decode_pathspec(encoded_pathspec))
        except Exception as e:
            logging.warn('Failed to find or open file entry')
            logging.debug(encoded_pathspec)
            logging.debug(e.message)
            logging.debug(traceback.format_exc())
            abort(404, 'Failed to find or open file entry')

    def get_inode(self, encoded_pathspec):
        return self._decode_pathspec(encoded_pathspec).inode

    def get_file_path(self, encoded_pathspec):
        """Returns the full path of the given path spec"""
        return self._decode_pathspec(encoded_pathspec).location

    def get_file_name(self, encoded_pathspec):
        """Returns the file name with extension of the given path spec"""
        return os.path.basename(self.get_file_path(encoded_pathspec))

    def get_file_directory(self, encoded_pathspec):
        """Returns the full path of the parent directory of the given path spec"""
        return os.path.dirname(self.get_file_path(encoded_pathspec))

    def get_file_extension(self, encoded_pathspec):
        """Returns the file extension of the given path spec"""
        return os.path.splitext(self.get_file_name(encoded_pathspec))[1][1:].lower() or ""

    def guess_file_mimetype(self, encoded_pathspec, ignore_cache=False):
        """Returns a mimetype based on the files extension"""
        if not ignore_cache and self.is_file_cached(encoded_pathspec):
            actual_mimetype = self.get_mimetype(encoded_pathspec, self.get_cache_path(encoded_pathspec))
            if actual_mimetype:
                return actual_mimetype
        return self.guess_mimetype(self.get_file_extension(encoded_pathspec))

    def _get_pathspec_hash(self, encoded_pathspec):
        """Returns the SHA1 hash of the path spec"""
        return hashlib.sha1(encoded_pathspec).hexdigest()

    def get_cache_directory(self, encoded_pathspec, parent_directory='files'):
        """Returns the full path of the directory that should contain the cached evidence file"""
        return self.output_dir + parent_directory + os.path.sep +\
               self._get_pathspec_hash(encoded_pathspec) + os.path.sep

    def get_cache_path(self, encoded_pathspec, parent_directory='files'):
        """Returns the full path to the cached evidence file"""
        return self.get_cache_directory(encoded_pathspec, parent_directory) + \
               unicode(self.get_file_name(encoded_pathspec))

    def is_file_cached(self, encoded_pathspec, parent_directory='files'):
        """Returns True if the evidence file is cached and false if it is not cached"""
        return os.path.isfile(self.get_cache_path(encoded_pathspec, parent_directory))

    def get_file_information(self, encoded_pathspec, pathspec):
        """Returns a dictionary of key information within a File Entry"""
        with self._read_lock:
            if encoded_pathspec in self._reading:
                self._reading[encoded_pathspec] += 1
            else:
                self._reading[encoded_pathspec] = 1

        efetch_dictionary = {}
        file_entry = self._get_file_entry(encoded_pathspec)

        if file_entry.IsFile() and pathspec.type_indicator == u'TSK':
            file_object = file_entry.GetFileObject()
            tsk_object = file_object._tsk_file
            file_type = tsk_object.info.meta.type
            if file_type == None:
                efetch_dictionary['meta_type'] = 'None'
            elif file_type == pytsk3.TSK_FS_META_TYPE_REG:
                efetch_dictionary['meta_type'] = 'File'
            elif file_type == pytsk3.TSK_FS_META_TYPE_DIR:
                efetch_dictionary['meta_type'] = 'Directory'
            elif file_type == pytsk3.TSK_FS_META_TYPE_LNK:
                efetch_dictionary['meta_type'] = 'Link'
            else:
                efetch_dictionary['meta_type'] = str(file_type)

            efetch_dictionary['mtime'] = datetime.datetime.utcfromtimestamp(
                tsk_object.info.meta.mtime).isoformat()
            efetch_dictionary['atime'] = datetime.datetime.utcfromtimestamp(
                tsk_object.info.meta.atime).isoformat()
            efetch_dictionary['ctime'] = datetime.datetime.utcfromtimestamp(
                tsk_object.info.meta.ctime).isoformat()
            efetch_dictionary['crtime'] = datetime.datetime.utcfromtimestamp(
                tsk_object.info.meta.crtime).isoformat()
            efetch_dictionary['size'] = str(tsk_object.info.meta.size)
            efetch_dictionary['uid'] = str(tsk_object.info.meta.uid)
            efetch_dictionary['gid'] = str(tsk_object.info.meta.gid)
            with self._read_lock:
                if self._reading[encoded_pathspec]  == 1:
                    # Attempt close again, if exception
                    try:
                        file_object.close()
                    except:
                        file_object.close()
        elif file_entry.IsDirectory():
            efetch_dictionary['meta_type'] = 'Directory'
        elif file_entry.IsFile():
            efetch_dictionary['meta_type'] = 'File'
            efetch_dictionary['size'] = [0]
        else:
            efetch_dictionary['meta_type'] = 'Unknown'

        with self._read_lock:
            self._reading[encoded_pathspec] -= 1

        return efetch_dictionary

    def get_efetch_dictionary(self, encoded_pathspec, index='*', cache=False, fast=False):
        """Creates and returns an Efetch object from an encoded path spec"""
        efetch_dictionary = {}
        efetch_dictionary['pathspec'] = encoded_pathspec
        efetch_dictionary['url_query'] = urlencode({ 'pathspec': encoded_pathspec,
                                                     'index': index})

        pathspec = self._decode_pathspec(encoded_pathspec)

        efetch_dictionary['path'] = pathspec.location
        efetch_dictionary['type_indicator'] = pathspec.type_indicator
        if efetch_dictionary['type_indicator'] == 'TSK':
            efetch_dictionary['inode'] = pathspec.inode
        efetch_dictionary['file_name'] = os.path.basename(efetch_dictionary['path'])
        efetch_dictionary['directory'] = os.path.dirname(efetch_dictionary['path'])
        efetch_dictionary['extension'] = os.path.splitext(efetch_dictionary['file_name'])[1][1:].lower() or ""
        efetch_dictionary['mime_type'] = self.guess_mimetype(efetch_dictionary['extension'])
        efetch_dictionary['file_cache_path'] = self.get_cache_path(encoded_pathspec)
        efetch_dictionary['file_cache_dir'] = self.get_cache_directory(encoded_pathspec)
        efetch_dictionary['thumbnail_cache_path'] = self.get_cache_path(encoded_pathspec, 'thumbnails')
        efetch_dictionary['thumbnail_cache_dir'] = self.get_cache_directory(encoded_pathspec, 'thumbnails')

        if not fast:
            efetch_dictionary.update(self.get_file_information(encoded_pathspec, pathspec))

        if os.path.isfile(efetch_dictionary['file_cache_path']):
            efetch_dictionary['cached'] = True
            efetch_dictionary['mimetype'] = self.guess_file_mimetype(encoded_pathspec)
            efetch_dictionary['mimetype_known'] = True
        elif cache:
            efetch_dictionary['cached'] = self.cache_file(efetch_dictionary)
            efetch_dictionary['mimetype'] = self.guess_file_mimetype(encoded_pathspec)
            efetch_dictionary['mimetype_known'] = True
        else:
            efetch_dictionary['cached'] = False
            efetch_dictionary['mimetype'] = self.guess_mimetype(efetch_dictionary['extension'])
            efetch_dictionary['mimetype_known'] = False

        return efetch_dictionary

    def cache_file(self, efetch_dictionary, file_entry=False):
        """Caches the provided file and returns the files cached directory"""
        if efetch_dictionary['meta_type'] != 'File':
            return False
        if int(efetch_dictionary['size'][0]) > self.max_file_size:
            return False

        if not os.path.isdir(efetch_dictionary['file_cache_dir']):
            os.makedirs(efetch_dictionary['file_cache_dir'])

        with self._cache_lock:
            if not os.path.isfile(efetch_dictionary['file_cache_path']):
                with self._read_lock:
                    if efetch_dictionary['pathspec'] in self._reading:
                        self._reading[efetch_dictionary['pathspec']] += 1
                    else:
                        self._reading[efetch_dictionary['pathspec']] = 1
                self._caching.append(efetch_dictionary['pathspec'])
                if not file_entry:
                    file_entry = self._get_file_entry(efetch_dictionary['pathspec'])
                in_file = file_entry.GetFileObject()
                out_file = open(efetch_dictionary['file_cache_path'], "wb")
                data = in_file.read(32768)
                while data:
                    out_file.write(data)
                    data = in_file.read(32768)
                out_file.close()

                with self._read_lock:
                    if self._reading[efetch_dictionary['pathspec']] == 1:
                        # del file_entry
                        in_file.close()
                    self._reading[efetch_dictionary['pathspec']] -= 1
                self._caching.remove(efetch_dictionary['pathspec'])

        # If the file is an image create a thumbnail
        if self.get_mimetype(efetch_dictionary['pathspec'],
                             efetch_dictionary['file_cache_path']).startswith('image') \
                and not os.path.isfile(efetch_dictionary['thumbnail_cache_path']):
            if not os.path.isdir(efetch_dictionary['thumbnail_cache_dir']):
                os.makedirs(efetch_dictionary['thumbnail_cache_dir'])
            try:
                image = Image.open(efetch_dictionary['file_cache_path'])
                image.thumbnail((64,64), Image.ANTIALIAS)
                if efetch_dictionary['mimetype'] == 'image/jpeg':
                    image.save(efetch_dictionary['thumbnail_cache_path'], 'JPEG')
                else:
                    image.save(efetch_dictionary['thumbnail_cache_path'])
            except IOError:
                logging.warn('IOError when trying to create thumbnail for '
                             + efetch_dictionary['file_name'] + ' at cached path ' +
                             efetch_dictionary['file_cache_path'])
            except:
                logging.warn('Failed to create thumbnail for ' + efetch_dictionary['file_name'] +
                             ' at cached path ' + efetch_dictionary['file_cache_path'])

        return True

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