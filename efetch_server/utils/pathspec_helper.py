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
import json
import re
import threading
import traceback
import time
from bottle import abort
from dfvfs.lib import definitions
from dfvfs.lib.errors import AccessError, CacheFullError
import dfvfs.path
from dfvfs.path.zip_path_spec import ZipPathSpec
from dfvfs.resolver import resolver
from dfvfs.serializer.json_serializer import JsonPathSpecSerializer
from dfvfs.lib import definitions as dfvfs_definitions
from dfvfs.path import factory as path_spec_factory
from dfvfs.analyzer.analyzer import Analyzer
from PIL import Image
from urllib import urlencode
from efetch_server.utils.dfvfs_util import DfvfsUtil

class PathspecHelper(object):
    """This singleton class provides helper methods that generally all take a pathspec"""
    # Objects for controlling caching (Only 1 file caches at a time)
    _cache_lock = threading.Lock()
    _caching = []
    # Objects for controlling evidence file reads (Only 1 file read at a time)
    _file_read_lock = threading.Lock()
    # Objects for controlling running magic on a file (Only 1 file at a time)
    _magic = threading.Lock()
    # Objects for controlling file entry objects
    _open_file_entries_lock = threading.Lock()
    _open_file_entries_locks = {}
    _open_file_entries_count = {}
    _open_file_entries = {}
    # Objects for controlling opening and closing of file objects
    _open_file_object_lock = threading.Lock()
    _open_file_objects_count = {}
    _open_file_objects = {}
    # Misc
    _max_file_count = 256
    _cache_chunk_size = 32768
    _thumbnail_size = 64
    _mimetype_chunk_size = 32768

    _automatically_traverse = ['VSHADOW', 'TSK_PARTITION', 'EWF']

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

    def _get_stat_information(self, encoded_pathspec):
        """Creates a dictionary of information about the pathspec"""
        file_entry = PathspecHelper._open_file_entry(encoded_pathspec)

        evidence_item = self._get_stat_information_from_file_entry(file_entry)

        del file_entry
        PathspecHelper._close_file_entry(encoded_pathspec)

        return  evidence_item

    def _get_stat_information_from_file_entry(self, file_entry):
        """Creates a dictionary of information about the file_entry"""
        evidence_item = {}
        stat_object = file_entry.GetStat()

        for attribute in [ 'mode', 'uid', 'gid']:
            evidence_item[attribute] = str(getattr(stat_object, attribute, ''))

        try:
            evidence_item['size'] = int(getattr(stat_object, 'size', 0))
        except TypeError:
            logging.warn('Evidence size not an int, setting size to 0')
            evidence_item['size'] = 0


        # TODO Take in flag from efetch -z to specify timezone
        for attribute in ['mtime', 'atime', 'ctime', 'crtime']:
            value = getattr(stat_object, attribute, False)
            if value:
                evidence_item[attribute] = datetime.datetime.utcfromtimestamp(value).isoformat()

        evidence_item['inode'] = getattr(stat_object, 'ino', '')

        type = getattr(stat_object, 'type', '')
        if type:
            if type == definitions.FILE_ENTRY_TYPE_DEVICE:
                # TODO CHANGE
                evidence_item['meta_type'] = 'Device'
                evidence_item['legacy_type'] = 'b/b'
                analyze = Analyzer()
                try:
                    volume_type = analyze.GetVolumeSystemTypeIndicators(file_entry.path_spec)
                    if volume_type:
                        evidence_item['volume_type'] = volume_type
                    storage_type = analyze.GetStorageMediaImageTypeIndicators(file_entry.path_spec)
                    if storage_type:
                        evidence_item['storage_type'] = storage_type
                    compression_type = analyze.GetCompressedStreamTypeIndicators(file_entry.path_spec)
                    if compression_type:
                        evidence_item['compression_type'] = compression_type
                    archive_type = analyze.GetArchiveTypeIndicators(file_entry.path_spec)
                    if archive_type:
                        evidence_item['archive_type'] = archive_type
                except AccessError:
                    logging.debug('Failed to determine volume or storage type of because access was denied')
                except IOError:
                    logging.debug('IOError on device')

            elif type == definitions.FILE_ENTRY_TYPE_DIRECTORY:
                evidence_item['meta_type'] = 'Directory'
                evidence_item['legacy_type'] = 'd/d'
            elif type == definitions.FILE_ENTRY_TYPE_FILE:
                evidence_item['meta_type'] = 'File'
                evidence_item['legacy_type'] = 'r/r'
                analyze = Analyzer()
                try:
                    volume_type = analyze.GetVolumeSystemTypeIndicators(file_entry.path_spec)
                    if volume_type:
                        evidence_item['volume_type'] = volume_type
                    storage_type = analyze.GetStorageMediaImageTypeIndicators(file_entry.path_spec)
                    if storage_type:
                        evidence_item['storage_type'] = storage_type
                    compression_type = analyze.GetCompressedStreamTypeIndicators(file_entry.path_spec)
                    if compression_type:
                        evidence_item['compression_type'] = compression_type
                    archive_type = analyze.GetArchiveTypeIndicators(file_entry.path_spec)
                    if archive_type:
                        evidence_item['archive_type'] = archive_type
                except AccessError:
                    logging.warn('Failed to determine volume or storage type of because access was denied')
            elif type == definitions.FILE_ENTRY_TYPE_LINK:
                evidence_item['meta_type'] = 'Link'
                evidence_item['legacy_type'] = 'l/l'
            elif type == definitions.FILE_ENTRY_TYPE_SOCKET:
                evidence_item['meta_type'] = 'Socket'
                evidence_item['legacy_type'] = 'h/h'
            elif type == definitions.FILE_ENTRY_TYPE_PIPE:
                evidence_item['meta_type'] = 'Pipe'
                evidence_item['legacy_type'] = 'p/p'
            else:
                evidence_item['meta_type'] = 'Unknown'
        else:
            evidence_item['meta_type'] = 'Unknown'

        return  evidence_item

    def get_evidence_item(self, encoded_pathspec, index='*', cache=False, fast=False):
        """Creates and returns an Efetch object from an encoded path spec"""
        evidence_item = {}
        evidence_item['pathspec'] = encoded_pathspec
        evidence_item['url_query'] = urlencode({'pathspec': encoded_pathspec,
                                                'index': index})

        pathspec = PathspecHelper._decode_pathspec(encoded_pathspec)

        evidence_item['path'] = getattr(pathspec, 'location', '')
        if evidence_item['path'].endswith('/') or evidence_item['path'].endswith('\\'):
            evidence_item['path'] = evidence_item['path'][:-1]
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
            evidence_item.update(self._get_stat_information(encoded_pathspec))
        else:
            try:
                file_entry = PathspecHelper._open_file_entry(encoded_pathspec)

                if not file_entry:
                    evidence_item['meta_type'] = 'None'
                elif file_entry.IsDirectory():
                    evidence_item['meta_type'] = 'Directory'
                elif file_entry.IsFile():
                    evidence_item['meta_type'] = 'File'
                else:
                    evidence_item['meta_type'] = 'Unknown'

                del file_entry

                PathspecHelper._close_file_entry(encoded_pathspec)
            except RuntimeError:
                logging.warn('Failed to open file_entry for evidence')
                evidence_item['meta_type'] = 'Unknown'

        return self._append_mimetype(evidence_item, cache)

    def _append_mimetype(self, evidence, cache=False):
        evidence['mimetype'] = ''

        if cache:
            evidence['cached'] = self.cache_evidence_item(evidence)
            if evidence['cached']:
                evidence['mimetype'] = self.get_mimetype_from_path(evidence['file_cache_path'])
                evidence['mimetype_known'] = True
            else:
                evidence['mimetype'] = PathspecHelper.guess_mimetype(evidence['extension'])
                evidence['mimetype_known'] = False
        elif os.path.isfile(evidence['file_cache_path']) and \
                not evidence['pathspec'] in PathspecHelper._caching:
            evidence['mimetype'] = self.get_mimetype_from_path(evidence['file_cache_path'])
            evidence['mimetype_known'] = True
            evidence['cached'] = True
        else:
            evidence['mimetype'] = PathspecHelper.guess_mimetype(evidence['extension'])
            evidence['mimetype_known'] = False
            evidence['cached'] = False

        return evidence

    def cache_evidence_item(self, evidence_item, file_entry=False, repeat=4):
        """Caches the file object associated with the specified pathspec"""
        if evidence_item['meta_type'] != 'File':
            return False
        if int(evidence_item['size']) > self.max_file_size:
            return False

        if not os.path.isdir(evidence_item['file_cache_dir']):
            os.makedirs(evidence_item['file_cache_dir'])

        while not os.path.isfile(evidence_item['file_cache_path']) and repeat > 0:
            with PathspecHelper._cache_lock:
                repeat = repeat - 1
                #try:
                PathspecHelper._caching.append(evidence_item['pathspec'])
                in_file = PathspecHelper._open_file_object(evidence_item['pathspec'])
                out_file = open(evidence_item['file_cache_path'], "wb")
                with PathspecHelper._file_read_lock:
                    data = in_file.read(PathspecHelper._cache_chunk_size)
                    while data:
                        out_file.write(data)
                        data = in_file.read(PathspecHelper._cache_chunk_size)
                    in_file.seek(0)
                PathspecHelper._close_file_object(evidence_item['pathspec'])
                out_file.close()
                PathspecHelper._caching.remove(evidence_item['pathspec'])
                #except:
                #    logging.warn('File failed to cache, attempting ' + str(repeat) + ' more times')

        self.create_thumbnail(evidence_item, file_entry)

        return True

    def create_thumbnail(self, evidence_item, file_entry=False):
        """Creates a thumbnail for the evidence item"""
        # If the file is an image create a thumbnail
        if evidence_item['mimetype'].startswith('image') \
                and not os.path.isfile(evidence_item['thumbnail_cache_path']):
            if not os.path.isdir(evidence_item['thumbnail_cache_dir']):
                os.makedirs(evidence_item['thumbnail_cache_dir'])
            try:
                cached = os.path.isfile(evidence_item['file_cache_path'])
                if cached:
                    image = Image.open(evidence_item['file_cache_path'])
                else:
                    image = Image.open(self._open_file_object(evidence_item['pathspec']))

                image.thumbnail((PathspecHelper._thumbnail_size, PathspecHelper._thumbnail_size), Image.ANTIALIAS)

                if evidence_item['mimetype'] == 'image/jpeg':
                    image.save(evidence_item['thumbnail_cache_path'], 'JPEG')
                else:
                    image.save(evidence_item['thumbnail_cache_path'])

                if not cached:
                    self._close_file_object(evidence_item['pathspec'])
            except IOError:
                logging.warn('IOError when trying to create thumbnail for '
                             + evidence_item['file_name'] + ' at cached path ' +
                             evidence_item['file_cache_path'])
            except:
                logging.warn('Failed to create thumbnail for ' + evidence_item['file_name'] +
                             ' at cached path ' + evidence_item['file_cache_path'])

    def get_mimetype(self, encoded_pathspec, file_entry=None):
        """Gets the mimetype of the given pathspec"""
        data = PathspecHelper.read_file(encoded_pathspec, file_entry, size=self._mimetype_chunk_size)
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

    def list_directory(self, encoded_pathspec, recursive=False, index='*', auto_skip=True):
        """Lists a directory using a pathspec or list of pathspecs"""
        directories = self._list_directory(self._open_file_entry(encoded_pathspec), recursive, 0, index)
        self._close_file_entry(encoded_pathspec)
        return directories

    def _list_directory(self, file_entry, recursive=False, depth=0, index='*'):
        """Lists a directory using a file entry"""
        directory_list = []

        if depth > 0:
            evidence = {}
            pathspec = file_entry.path_spec
            evidence['pathspec'] = JsonPathSpecSerializer.WriteSerialized(pathspec)
            evidence['url_query'] = urlencode({'pathspec': evidence['pathspec'], 'index': index})
            evidence['path'] = pathspec.location
            location = pathspec.location
            if location.endswith('/') or location.endswith('\\'):
                location = location[:-1]
            file_name = os.path.basename(location)
            evidence['file_name'] = file_name
            evidence.update(self._get_stat_information_from_file_entry(file_entry))
            evidence['file_cache_path'] = self.get_cache_path(evidence['pathspec'])
            evidence['extension'] = self.get_file_extension(evidence['pathspec'])
            directory_list.append(self._append_mimetype(evidence))

        if (recursive or depth == 0) and (file_entry.IsDirectory() or hasattr(file_entry, 'sub_file_entries')):
            for sub_file_entry in file_entry.sub_file_entries:
                directory_list.extend(self._list_directory(sub_file_entry, recursive, depth + 1))

        return directory_list

    def old_list_directory(self, encoded_pathspec, recursive=False):
        """Lists a directory using a pathspec or list of pathspecs"""
        directory_list = []
        pathspec = PathspecHelper._decode_pathspec(encoded_pathspec)

        directory_list.extend(self._list_directory(
            resolver.Resolver.OpenFileEntry(pathspec), recursive, 0))

        return directory_list

    def _old_list_directory(self, file_entry, recursive=False, depth=0):
        """Lists a directory using a file entry"""
        directory_list = []

        if depth > 0:
            directory_list.append(self.get_evidence_item(JsonPathSpecSerializer.WriteSerialized(file_entry.path_spec)))

        if (recursive or depth == 0) and file_entry.IsDirectory():
            for sub_file_entry in file_entry.sub_file_entries:
                directory_list.extend(self._list_directory(sub_file_entry, recursive, depth + 1))

        return directory_list

    @staticmethod
    def _decode_pathspec(encoded_pathspec):
        """Returns a Path Spec object from an encoded path spec, causes a 400 abort if the decode fails"""
        if not encoded_pathspec:
            logging.warn('Path Spec required but none found')
            abort(400, 'Expected an encoded Path Spec, but none found')

        return JsonPathSpecSerializer.ReadSerialized(encoded_pathspec)

    @staticmethod
    def get_inode(encoded_pathspec):
        """Returns the inode for the given pathspec"""
        return PathspecHelper._decode_pathspec(encoded_pathspec).inode
    
    @staticmethod
    def get_file_path(encoded_pathspec):
        """Returns the full path of the given pathspec"""
        return getattr(PathspecHelper._decode_pathspec(encoded_pathspec), 'location', '')
    
    @staticmethod
    def get_file_name(encoded_pathspec):
        """Returns the file name with extension of the given pathspec"""
        file_name = os.path.basename(PathspecHelper.get_file_path(encoded_pathspec))
        if not file_name:
            file_name = 'none'
        return file_name
    
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
    def _open_file_entry(encoded_pathspec):
        """Returns an open File Entry object of the given path spec"""
        with PathspecHelper._open_file_entries_lock:
            if encoded_pathspec not in PathspecHelper._open_file_entries_locks:
                PathspecHelper._open_file_entries_locks[encoded_pathspec] = threading.Lock()

        with PathspecHelper._open_file_entries_locks[encoded_pathspec]:
            if encoded_pathspec in PathspecHelper._open_file_entries:
                PathspecHelper._open_file_entries_count[encoded_pathspec] += 1
                if PathspecHelper._open_file_entries[encoded_pathspec]:
                    return PathspecHelper._open_file_entries[encoded_pathspec]
            try:
                PathspecHelper._open_file_entries_count[encoded_pathspec] = 1
                try:
                    PathspecHelper._open_file_entries[encoded_pathspec] =\
                        resolver.Resolver.OpenFileEntry(PathspecHelper._decode_pathspec(encoded_pathspec))
                except KeyError:
                    logging.warn('Unknown KEY ERROR while opening evidence file, attempting again...')
                    PathspecHelper._open_file_entries[encoded_pathspec] = \
                        resolver.Resolver.OpenFileEntry(PathspecHelper._decode_pathspec(encoded_pathspec))
                except RuntimeError:
                    logging.warn('Unknown RUNTIME ERROR while opening evidence file, attempting again...')
                    PathspecHelper._open_file_entries[encoded_pathspec] = \
                        resolver.Resolver.OpenFileEntry(PathspecHelper._decode_pathspec(encoded_pathspec))
                except AttributeError:
                    logging.warn('Unknown ATTRIBUTE ERROR while opening evidence file, attempting again...')
                    PathspecHelper._open_file_entries[encoded_pathspec] = \
                        resolver.Resolver.OpenFileEntry(PathspecHelper._decode_pathspec(encoded_pathspec))
                except CacheFullError:
                    PathspecHelper._clear_file_entry_cache()
                    PathspecHelper._open_file_entries[encoded_pathspec] = \
                        resolver.Resolver.OpenFileEntry(PathspecHelper._decode_pathspec(encoded_pathspec))

                if not PathspecHelper._open_file_entries[encoded_pathspec]:
                    # TODO There appears to be a bug in dfVFS
                    # TODO     for compressed formats ZIP, etc.
                    logging.warn('Attempting compression error fix...')
                    type_indicator_list = ['ZIP', 'GZIP']
                    pathspec_dictionary = json.loads(encoded_pathspec)
                    # TODO add levels to repeat current_level = 0
                    if pathspec_dictionary['type_indicator'] in type_indicator_list:
                        pathspec_dictionary['location'] = pathspec_dictionary['location'] + u'/'
                    new_encoded_pathspec = json.dumps(pathspec_dictionary)
                    PathspecHelper._open_file_entries[encoded_pathspec] = \
                        resolver.Resolver.OpenFileEntry(PathspecHelper._decode_pathspec(new_encoded_pathspec))
                if PathspecHelper._open_file_entries[encoded_pathspec]:
                    return PathspecHelper._open_file_entries[encoded_pathspec]
            except Exception as e:
                del PathspecHelper._open_file_entries_count[encoded_pathspec]
                logging.error('Failed second attempt to open evidence file entry')
                logging.debug(encoded_pathspec)
                logging.debug(e.message)
                logging.debug(traceback.format_exc())
                raise RuntimeError('Failed to open evidence file entry')
        logging.error('Missing file entry for pathspec "' + encoded_pathspec + '"')
        raise RuntimeError('Missing File Entry for Pathspec')

    @staticmethod
    def _clear_file_entry_cache():
        logging.warn('File Entry cache is full, attempting to empty cache')
        with PathspecHelper._open_file_entries_lock:
            temp_locks = PathspecHelper._open_file_entries_locks.iteritems()
            keys_to_delete = []
            for key, lock in temp_locks:
                if not lock.locked():
                    keys_to_delete.append(key)
            for key in keys_to_delete:
                if key in PathspecHelper._open_file_entries_locks:
                    del PathspecHelper._open_file_entries_locks[key]
                if key in PathspecHelper._open_file_entries_count:
                    del PathspecHelper._open_file_entries_count[key]
                if key in PathspecHelper._open_file_entries:
                    del PathspecHelper._open_file_entries[key]
        time.sleep(0.1)

    @staticmethod
    def _close_file_entry(encoded_pathspec):
        """Closes the file entry"""
        try:
            with PathspecHelper._open_file_entries_lock:
                PathspecHelper._open_file_entries_count[encoded_pathspec] -= 1
                # TODO Determine a limit to the number of open files to store, currently waits until cache is full
                # if PathspecHelper._open_file_entries_count[encoded_pathspec] < 1:
                #     del PathspecHelper._open_file_entries[encoded_pathspec]
                #     del PathspecHelper._open_file_entries_locks[encoded_pathspec]
        except KeyError:
            logging.error('Attempted to close already closed file entry!')
            raise RuntimeError('Attempting to close already closed file entry')

    @staticmethod
    def read_file(encoded_pathspec, file_entry=False, size=0, seek=0):
        """Reads the file object from the specified pathspec, always seeks back to the beginning"""
        file = PathspecHelper._open_file_object(encoded_pathspec)
        with PathspecHelper._file_read_lock:
            file.seek(seek)
            if size:
                data = file.read(size)
            else:
                data = file.read()
            file.seek(0)
        PathspecHelper._close_file_object(encoded_pathspec)
        return data

    @staticmethod
    def _open_file_object(encoded_pathspec):
        """Returns the file object from the specified pathspec"""
        with PathspecHelper._open_file_object_lock:
            if len(PathspecHelper._open_file_objects) < PathspecHelper._max_file_count:
                if encoded_pathspec in PathspecHelper._open_file_objects_count:
                    PathspecHelper._open_file_objects_count[encoded_pathspec] += 1
                else:
                    PathspecHelper._open_file_objects_count[encoded_pathspec] = 1

                if encoded_pathspec not in PathspecHelper._open_file_objects:
                    file_entry = PathspecHelper._open_file_entry(encoded_pathspec)
                    if not file_entry.IsFile() and not file_entry.IsDevice():
                        PathspecHelper._close_file_entry(encoded_pathspec)
                        raise TypeError('Cannot open file object, because the pathspec is not for a file or device.')

                    try:
                        PathspecHelper._open_file_objects[encoded_pathspec] = file_entry.GetFileObject()
                    except SystemError:
                        logging.warn('System Error while trying to get file object, attempting again.')
                        PathspecHelper._open_file_objects[encoded_pathspec] = file_entry.GetFileObject()

                    PathspecHelper._close_file_entry(encoded_pathspec)

                return PathspecHelper._open_file_objects[encoded_pathspec]

    @staticmethod
    def _close_file_object(encoded_pathspec):
        """Closes the file object associated with the specified pathspec"""
        with PathspecHelper._open_file_object_lock:
            try:
                PathspecHelper._open_file_objects_count[encoded_pathspec] -= 1
                if PathspecHelper._open_file_objects_count[encoded_pathspec] < 1:
                    PathspecHelper._open_file_objects[encoded_pathspec].close()
                    del PathspecHelper._open_file_objects[encoded_pathspec]
                    PathspecHelper._close_file_entry(encoded_pathspec)
            except KeyError:
                logging.error('Attempted to close already closed file object!')
                raise RuntimeError('Attempting to close already closed file object')

    @staticmethod
    def get_base_pathspecs(evidence):
        '''Gets the base pathspec for the given evidence'''
        decoded_pathspec = PathspecHelper._decode_pathspec(evidence['pathspec'])
        if u'archive_type' in evidence and u'ZIP' in evidence['archive_type']:
            #pathspec = ZipPathSpec(location='/', parent=decoded_pathspec)
            pathspec = path_spec_factory.Factory.NewPathSpec(dfvfs_definitions.TYPE_INDICATOR_ZIP, location=u'/',
                                                             parent=decoded_pathspec)
        elif u'compression_type' in evidence and u'GZIP' in evidence['compression_type']:
            pathspec = path_spec_factory.Factory.NewPathSpec(dfvfs_definitions.TYPE_INDICATOR_GZIP,
                                                             parent=decoded_pathspec)
        elif u'compression_type' in evidence and u'BZIP2' in evidence['compression_type']:
            pathspec = path_spec_factory.Factory.NewPathSpec(
                dfvfs_definitions.TYPE_INDICATOR_COMPRESSED_STREAM,
                compression_method=dfvfs_definitions.COMPRESSION_METHOD_BZIP2,
                parent=decoded_pathspec)
        elif u'archive_type' in evidence and u'TAR' in evidence['archive_type']:
            pathspec = dfvfs.path.tar_path_spec.TARPathSpec(location='/', parent=decoded_pathspec)
        else:
            return PathspecHelper.get_new_base_pathspecs(evidence['pathspec'])

        encoded_base_pathspec = JsonPathSpecSerializer.WriteSerialized(pathspec)
        if hasattr(pathspec, 'location'):
            location = pathspec.location
            if location.endswith('/') or location.endswith('\\'):
                location = location[:-1]
            file_name = os.path.basename(location)
        else:
            file_name = '/'

        return [{'pathspec': encoded_base_pathspec, 'file_name': file_name}]

    # TODO Proper naming
    @staticmethod
    def get_new_base_pathspecs(encoded_pathspec):
        '''Gets a list of the base_pathspecs from in a pathspec'''
        try:
            dfvfs_util = DfvfsUtil(PathspecHelper._decode_pathspec(encoded_pathspec), interactive=True, is_pathspec=True)
        except CacheFullError:
            PathspecHelper._clear_file_entry_cache()
            dfvfs_util = DfvfsUtil(PathspecHelper._decode_pathspec(encoded_pathspec), interactive=True, is_pathspec=True)

        pathspec = dfvfs_util.base_path_specs

        if not isinstance(pathspec, list):
            pathspec = [pathspec]

        pathspecs = []

        for item in pathspec:
            if hasattr(item.parent, 'location'):
                file_name = item.parent.location
            else:
                file_name = '/'
            new_encoded_pathspec = JsonPathSpecSerializer.WriteSerialized(item)
            pathspecs.append({'pathspec': new_encoded_pathspec,
                              'url_query':  urlencode({'pathspec': new_encoded_pathspec}),
                              'file_name': file_name})

        return pathspecs

    # TODO, FIRST MOVE UP BY LOCATION i.e.: /tmp/test/file.txt > /tmp/test > /tmp > / > pathspec['parent']
    @staticmethod
    def get_parent_base_pathspecs(encoded_pathspec):
        pathspec = PathspecHelper._decode_pathspec(encoded_pathspec)
        parent = getattr(pathspec, 'parent', False)
        if parent:
            return parent

        return False

    # TODO RENAME THIS AND THE ABOVE METHOD AND ADD COMMENTS
    @staticmethod
    def get_parent_base_pathspecs_encoded(encoded_pathspec):
        return JsonPathSpecSerializer.WriteSerialized(PathspecHelper.get_parent_base_pathspecs(encoded_pathspec))

    @staticmethod
    def get_parent_pathspec(encoded_pathspec):
        '''Gets the parent pathspec of the provided pathspec'''
        file_entry = PathspecHelper._open_file_entry(encoded_pathspec)
        parent_entry = file_entry.GetParentFileEntry()
        PathspecHelper._close_file_entry(encoded_pathspec)

        if not parent_entry:
            parent_path_spec = PathspecHelper.get_parent_base_pathspecs(encoded_pathspec)
        else:
            parent_path_spec = parent_entry.path_spec

        if not parent_path_spec:
            return False

        # TODO FOR EXPANDABLE EVIDENCE IF NO CHILDREN, AUTOMATICALLY MOVE UP A DIRECTORY
        # # TODO This needs more then just VSHADOW, should probably have partitions and possibly encryptions
        while getattr(parent_path_spec, 'type_indicator', '') in PathspecHelper._automatically_traverse:
           parent_path_spec = parent_path_spec.parent

        return JsonPathSpecSerializer.WriteSerialized(parent_path_spec)

    @staticmethod
    def get_pathspec(pathspec_or_source):
        """Gets the pathspec"""
        try:
            pathspec = DfvfsUtil.decode_pathspec(pathspec_or_source)
        except:
            try:
                dfvfs_util = DfvfsUtil(pathspec_or_source)
            except CacheFullError:
                PathspecHelper._clear_file_entry_cache()
                dfvfs_util = DfvfsUtil(pathspec_or_source)
            pathspec = dfvfs_util.base_path_specs

        # TODO remove because some cases will want all possible pathspecs
        if isinstance(pathspec, list):
            pathspec = pathspec[0]

        return pathspec

    @staticmethod
    def get_encoded_pathspec(pathspec_or_source):
        """Gets the encoded pathspec"""
        return JsonPathSpecSerializer.WriteSerialized(PathspecHelper.get_pathspec(pathspec_or_source))

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
            'docx'   : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'dot'    : 'application/msword',
            'dotx'   : 'application/vnd.openxmlformats-officedocument.wordprocessingml.template',
            'dvi'    : 'application/x-dvi',
            'eml'    : 'message/rfc822',
            'eps'    : 'application/postscript',
            'etx'    : 'text/x-setext',
            'exe'    : 'application/x-dosexec',
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
            'pptx'   : 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'potx'   : 'application/vnd.openxmlformats-officedocument.presentationml.template',
            'ppsx'   : 'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
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
            'xlsx'   : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'xltx'   : 'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
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