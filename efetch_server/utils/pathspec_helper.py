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
import re
import threading
import time
import traceback
from bottle import abort
from dfvfs.resolver import resolver
from dfvfs.serializer.json_serializer import JsonPathSpecSerializer
from PIL import Image
from urllib import urlencode

# TODO - Currently Mimetype is only accurately accessed if file is cached
# TODO - Determine best approach for giving mimetype without slowing down everything
class PathspecHelper(object):
    """This singleton class provides helper methods that generally all take a pathspec"""
    _cache_lock = threading.Lock()
    _source_read_lock = threading.Lock()
    _file_read_lock = threading.Lock()
    _open_lock = threading.Lock()
    _magic = threading.Lock()
    _caching = []
    _reading = {}
    _open_files = {}
    _max_file_count = 256
    _cache_chunk_size = 32768
    _thumbnail_size = 64
    instance = None

    class __PathspecHelper(object):
        def __init__(self, output_directory, max_file_size):
            self.output_directory = output_directory
            self.max_file_size = max_file_size
            
            # Determine which magic lib to use
            try:
                self._my_magic = magic.Magic(mime=True)
                self._pymagic = True
            except:
                self._my_magic = magic.Magic(flags=magic.MAGIC_MIME_TYPE)
                self._pymagic = False
        
    def __init__(self, output_directory, max_file_size):
        """Initializes the Efetch Helper"""
        if not PathspecHelper.instance:
            PathspecHelper.instance = PathspecHelper.__PathspecHelper(output_directory, max_file_size)
        else:
            logging.warn('Cannot reinitialize Pathspec Helper')

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def get_cache_path(self, encoded_pathspec, parent_directory='files'):
        """Returns the full path to the cached evidence file"""
        return self.get_cache_directory(encoded_pathspec, parent_directory) + \
               unicode(PathspecHelper.get_file_name(encoded_pathspec))

    def is_file_cached(self, encoded_pathspec, parent_directory='files'):
        """Returns True if the evidence file is cached and false if it is not cached"""
        return os.path.isfile(self.get_cache_path(encoded_pathspec, parent_directory))

    def get_cache_directory(self, encoded_pathspec, parent_directory='files'):
        """Returns the full path of the directory that should contain the cached evidence file"""
        return self.output_directory + parent_directory + os.path.sep + \
               PathspecHelper._get_pathspec_hash(encoded_pathspec) + os.path.sep

    def cache_file(self, encoded_pathspec, file_entry=False):
        """Caches the file object associated with the specified pathspec"""
        return self.cache_evidence_item(self.get_evidence_item(encoded_pathspec))

    def _get_file_information(self, encoded_pathspec, pathspec):
        """Returns a dictionary of key information within a File Entry"""
        evidence_item = {}
        self._open_file(encoded_pathspec)
        file_entry = PathspecHelper._get_file_entry(encoded_pathspec)

        if file_entry.IsFile() and pathspec.type_indicator == u'TSK':
            file_object = PathspecHelper._open_file(encoded_pathspec, file_entry)
            tsk_object = file_object._tsk_file
            file_type = tsk_object.info.meta.type
            if file_type == None:
                evidence_item['meta_type'] = 'None'
            elif file_type == pytsk3.TSK_FS_META_TYPE_REG:
                evidence_item['meta_type'] = 'File'
            elif file_type == pytsk3.TSK_FS_META_TYPE_DIR:
                evidence_item['meta_type'] = 'Directory'
            elif file_type == pytsk3.TSK_FS_META_TYPE_LNK:
                evidence_item['meta_type'] = 'Link'
            else:
                evidence_item['meta_type'] = str(file_type)

            evidence_item['mtime'] = datetime.datetime.utcfromtimestamp(
                tsk_object.info.meta.mtime).isoformat()
            evidence_item['atime'] = datetime.datetime.utcfromtimestamp(
                tsk_object.info.meta.atime).isoformat()
            evidence_item['ctime'] = datetime.datetime.utcfromtimestamp(
                tsk_object.info.meta.ctime).isoformat()
            evidence_item['crtime'] = datetime.datetime.utcfromtimestamp(
                tsk_object.info.meta.crtime).isoformat()
            evidence_item['size'] = str(tsk_object.info.meta.size)
            evidence_item['uid'] = str(tsk_object.info.meta.uid)
            evidence_item['gid'] = str(tsk_object.info.meta.gid)
            PathspecHelper._close_file(encoded_pathspec)
        elif file_entry.IsDirectory():
            evidence_item['meta_type'] = 'Directory'
        elif file_entry.IsFile():
            evidence_item['meta_type'] = 'File'
            evidence_item['size'] = [0]
        else:
            evidence_item['meta_type'] = 'Unknown'
        self._close_file(encoded_pathspec)

        return evidence_item

    def get_evidence_item(self, encoded_pathspec, index='*', cache=False, fast=False):
        """Creates and returns an Efetch object from an encoded path spec"""
        evidence_item = {}
        evidence_item['pathspec'] = encoded_pathspec
        evidence_item['url_query'] = urlencode({'pathspec': encoded_pathspec,
                                                'index': index})

        pathspec = PathspecHelper._decode_pathspec(encoded_pathspec)

        evidence_item['path'] = pathspec.location
        evidence_item['type_indicator'] = pathspec.type_indicator
        if evidence_item['type_indicator'] == 'TSK':
            evidence_item['inode'] = pathspec.inode
        evidence_item['file_name'] = os.path.basename(evidence_item['path'])
        evidence_item['directory'] = os.path.dirname(evidence_item['path'])
        evidence_item['extension'] = os.path.splitext(evidence_item['file_name'])[1][1:].lower() or ""
        evidence_item['file_cache_path'] = self.get_cache_path(encoded_pathspec)
        evidence_item['file_cache_dir'] = self.get_cache_directory(encoded_pathspec)
        evidence_item['thumbnail_cache_path'] = self.get_cache_path(encoded_pathspec, 'thumbnails')
        evidence_item['thumbnail_cache_dir'] = self.get_cache_directory(encoded_pathspec, 'thumbnails')
        if not fast:
            evidence_item.update(self._get_file_information(encoded_pathspec, pathspec))
        else:
            # TODO Remove:
            file_entry = PathspecHelper._get_file_entry(encoded_pathspec)
            if file_entry.IsDirectory():
                evidence_item['meta_type'] = 'Directory'
            elif file_entry.IsFile():
                evidence_item['meta_type'] = 'File'
            else:
                evidence_item['meta_type'] = 'Unknown'

        evidence_item['mimetype'] = 'Unknown'

        if cache:
            evidence_item['cached'] = self.cache_evidence_item(evidence_item)
            if evidence_item['cached']:
                evidence_item['mimetype'] = self.get_mimetype_from_path(evidence_item['file_cache_path'])
                evidence_item['mimetype_known'] = True
            else:
                evidence_item['mimetype'] = PathspecHelper.guess_mimetype(evidence_item['extension'])
                evidence_item['mimetype_known'] = False
        elif os.path.isfile(evidence_item['file_cache_path']) and \
                not evidence_item['pathspec'] in PathspecHelper._caching:
            evidence_item['mimetype'] = self.get_mimetype_from_path(evidence_item['file_cache_path'])
            evidence_item['mimetype_known'] = True
            evidence_item['cached'] = True
        else:
            evidence_item['mimetype'] = PathspecHelper.guess_mimetype(evidence_item['extension'])
            evidence_item['mimetype_known'] = False
            evidence_item['cached'] = False

        return evidence_item

    def cache_evidence_item(self, evidence_item, file_entry=False, repeat=4):
        """Caches the file object associated with the specified pathspec"""
        if evidence_item['meta_type'] != 'File':
            return False
        if int(evidence_item['size'][0]) > self.max_file_size:
            return False

        if not os.path.isdir(evidence_item['file_cache_dir']):
            os.makedirs(evidence_item['file_cache_dir'])

        while not os.path.isfile(evidence_item['file_cache_path']) and repeat > 0:
            with PathspecHelper._cache_lock:
                repeat = repeat - 1
                try:
                    PathspecHelper._caching.append(evidence_item['pathspec'])
                    in_file = PathspecHelper._open_file(evidence_item['pathspec'])
                    out_file = open(evidence_item['file_cache_path'], "wb")
                    with PathspecHelper._file_read_lock:
                        data = in_file.read(PathspecHelper._cache_chunk_size)
                        while data:
                            out_file.write(data)
                            data = in_file.read(PathspecHelper._cache_chunk_size)
                        in_file.seek(0)
                    PathspecHelper._close_file(evidence_item['pathspec'])
                    out_file.close()
                except:
                    logging.warn('File failed to cache, attempting ' + str(repeat) + ' more times')

        # If the file is an image create a thumbnail
        if evidence_item['mimetype'].startswith('image') \
                and not os.path.isfile(evidence_item['thumbnail_cache_path']):
            if not os.path.isdir(evidence_item['thumbnail_cache_dir']):
                os.makedirs(evidence_item['thumbnail_cache_dir'])
            try:
                image = Image.open(evidence_item['file_cache_path'])
                image.thumbnail((PathspecHelper._thumbnail_size, PathspecHelper._thumbnail_size), Image.ANTIALIAS)
                if evidence_item['mimetype'] == 'image/jpeg':
                    image.save(evidence_item['thumbnail_cache_path'], 'JPEG')
                else:
                    image.save(evidence_item['thumbnail_cache_path'])
            except IOError:
                logging.warn('IOError when trying to create thumbnail for '
                             + evidence_item['file_name'] + ' at cached path ' +
                             evidence_item['file_cache_path'])
            except:
                logging.warn('Failed to create thumbnail for ' + evidence_item['file_name'] +
                             ' at cached path ' + evidence_item['file_cache_path'])

        return True

    def get_mimetype(self, encoded_pathspec, file_entry=None):
        """Gets the mimetype of the given pathspec"""
        data = PathspecHelper.read_file(encoded_pathspec, file_entry)
        if not data:
            return 'Empty'

        # Do not remove this lock, it maybe a bug in magic, but it will break the code
        with self._magic:
            if self._pymagic:
                return self._my_magic.from_buffer(data)
            else:
                return self._my_magic.id_buffer(data)

    def get_mimetype_from_path(self, path):
        """Gets the mimetype from the file at the specified path"""
        # Do not remove this lock, it maybe a bug in magic, but it will break the code
        with self._magic:
            if self._pymagic:
                return self._my_magic.from_file(path)
            else:
                return self._my_magic.id_filename(path)

    @staticmethod
    def _decode_pathspec(encoded_pathspec):
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
    
    @staticmethod
    def _get_file_entry(encoded_pathspec):
        """Returns an open File Entry object of the given path spec, causes a 404 abort if the file is not found"""
        try:
            with PathspecHelper._file_read_lock:
                try:
                    return resolver.Resolver.OpenFileEntry(PathspecHelper._decode_pathspec(encoded_pathspec))
                except KeyError as e:
                    print('Unknown KEY ERROR')
                    return resolver.Resolver.OpenFileEntry(PathspecHelper._decode_pathspec(encoded_pathspec))
                except RuntimeError as r:
                    print('Unknown RUNTIME ERROR')
                    return resolver.Resolver.OpenFileEntry(PathspecHelper._decode_pathspec(encoded_pathspec))
        except Exception as e:
            logging.warn('Failed to find or open file entry')
            logging.debug(encoded_pathspec)
            logging.debug(e.message)
            logging.debug(traceback.format_exc())
            abort(404, 'Failed to find or open file entry')
    
    @staticmethod
    def get_inode(encoded_pathspec):
        """Returns the inode for the given pathspec"""
        return PathspecHelper._decode_pathspec(encoded_pathspec).inode
    
    @staticmethod
    def get_file_path(encoded_pathspec):
        """Returns the full path of the given pathspec"""
        return PathspecHelper._decode_pathspec(encoded_pathspec).location
    
    @staticmethod
    def get_file_name(encoded_pathspec):
        """Returns the file name with extension of the given pathspec"""
        return os.path.basename(PathspecHelper.get_file_path(encoded_pathspec))
    
    @staticmethod
    def get_file_directory(encoded_pathspec):
        """Returns the full path of the parent directory of the given pathspec"""
        return os.path.dirname(PathspecHelper.get_file_path(encoded_pathspec))
    
    @staticmethod
    def get_file_extension(encoded_pathspec):
        """Returns the file extension of the given pathspec"""
        return os.path.splitext(PathspecHelper.get_file_name(encoded_pathspec))[1][1:].lower() or ""
    
    @staticmethod
    def _get_pathspec_hash(encoded_pathspec):
        """Returns the SHA1 hash of the encoded pathspec, NOT THE FILE"""
        return hashlib.sha1(encoded_pathspec).hexdigest()

    @staticmethod
    def get_file_strings(encoded_pathspec, min=4):
        chars = r"A-Za-z0-9/\-:.,_$%'()[\]<> "
        regexp = '[%s]{%d,}' % (chars, min)
        pattern = re.compile(regexp)
        return pattern.findall(PathspecHelper.read_file(encoded_pathspec))
    
    @staticmethod
    def read_file(encoded_pathspec, file_entry=False):
        """Reads the file object from the specified pathspec"""
        file = PathspecHelper._open_file(encoded_pathspec, file_entry)
        with PathspecHelper._file_read_lock:
            data = file.read()
            file.seek(0)
        PathspecHelper._close_file(encoded_pathspec)
        return data

    # TODO Add specific exceptions, path not found, io error, not file
    # TODO Need a check to see if it is a file before doing all this
    @staticmethod
    def _open_file(encoded_pathspec, file_entry=False, sleep_time=1):
        """Returns the file object from the specified pathspec"""
        while True:
            with PathspecHelper._open_lock:
                if len(PathspecHelper._open_files) < PathspecHelper._max_file_count:
                    if encoded_pathspec in PathspecHelper._reading:
                        PathspecHelper._reading[encoded_pathspec] += 1
                    else:
                        PathspecHelper._reading[encoded_pathspec] = 1

                    if encoded_pathspec not in PathspecHelper._open_files:
                        if not file_entry:
                            file_entry = PathspecHelper._get_file_entry(encoded_pathspec)
                        try:
                            PathspecHelper._open_files[encoded_pathspec] = file_entry.GetFileObject()
                        except:
                            logging.warn('Failed to read file, is this pathspec a file?')
                            abort(400, 'Failed to read file, is this pathspec a file?')
                    return PathspecHelper._open_files[encoded_pathspec]
            time.sleep(sleep_time)

    @staticmethod
    def _close_file(encoded_pathspec):
        """Closes the file object associated with the specified pathspec"""
        with PathspecHelper._open_lock:
            PathspecHelper._reading[encoded_pathspec] -= 1
            if PathspecHelper._reading[encoded_pathspec] < 1:
                PathspecHelper._open_files[encoded_pathspec].close()
                del PathspecHelper._open_files[encoded_pathspec]

    @staticmethod
    def guess_mimetype(extension):
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
            return 'Unknown'