#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Simple utility for getting files and information from dfvfs."""

#This code is similar recursive_hasher example found on dfvfs github
#  at https://github.com/log2timeline/dfvfs/
#  This code is based on code by Joachim Metz

from __future__ import print_function
import argparse
import getpass
import hashlib
import logging
import os
import sys

from dfvfs.credentials import manager as credentials_manager
from dfvfs.helpers import source_scanner
from dfvfs.lib import definitions
from dfvfs.lib import errors
from dfvfs.resolver import resolver
from dfvfs.volume import tsk_volume_system
from dfvfs.volume import vshadow_volume_system
from dfvfs.vfs import file_system
from dfvfs.path import factory as path_spec_factory

class DfvfsUtil(object):
    """Class that provides a simple interface into dfvfs."""

    # Class constant that defines the default read buffer size.
    _READ_BUFFER_SIZE = 32768

    # For context see: http://en.wikipedia.org/wiki/Byte
    _UNITS_1000 = [u'B', u'kB', u'MB', u'GB', u'TB', u'EB', u'ZB', u'YB']
    _UNITS_1024 = [u'B', u'KiB', u'MiB', u'GiB', u'TiB', u'EiB', u'ZiB', u'YiB']

    base_path_specs = None

    def __init__(self, source):
        """Initializes the dfvfs util object."""
        super(DfvfsUtil, self).__init__()
        self._source_scanner = source_scanner.SourceScanner()
        self.base_path_specs = self.GetBasePathSpecs(source)

    def Icat(self, full_path, output_path, ignore_case = False):
        """Gets the file at full_path and outputs it to the output path"""
        in_file = self.GetFile(full_path, ignore_case)
        out_file = open(output_path,"wb")
        data = in_file.read(self._READ_BUFFER_SIZE)
        while data:
            out_file.write(data)
            data = in_file.read(self._READ_BUFFER_SIZE)
        out_file.close()

    def GetFile(self, full_path, ignore_case = False):
        """Gets file using the full path to the file"""
        if full_path.endswith('/'):
            full_path = full_path[:-1]
        paths = full_path.split('/')
        curr = 1
        for base_path_spec in self.base_path_specs:
            file_system = resolver.Resolver.OpenFileSystem(base_path_spec)
            file_entry = resolver.Resolver.OpenFileEntry(base_path_spec)     
            if file_entry is None:
                logging.warning(u'Unable to open base path specification:\n{0:s}'.format(base_path_spec.comparable))
            else:
                myfile = self._GetFile(curr, paths, file_entry, ignore_case)         
                if myfile is not None:
                    return myfile
                continue
    
    def ListDir(self, dir_path, recursive=False):
        """Lists the contents of the provided directory, can be set to list recursively"""
        if dir_path.endswith('/'):
            dir_path = dir_path[:-1]
        paths = dir_path.split('/')
        curr = 1

        if dir_path == '/' and not recursive:
            return self.ListRoot()

        for base_path_spec in self.base_path_specs:
            file_system = resolver.Resolver.OpenFileSystem(base_path_spec)
            file_entry = resolver.Resolver.OpenFileEntry(base_path_spec)     
            if file_entry is None:
                logging.warning(u'Unable to open base path specification:\n{0:s}'.format(base_path_spec.comparable))
            else:
                dir_list = self._ListDir(curr, paths, file_entry, recursive)
                if dir_list is not None:
                    return dir_list
                continue
    
    def FileExists(self, full_path, ignore_case=False):
        """Returns true if there is a file at the given full path or false if not"""
        paths = full_path.split('/')
        curr = 1
        for base_path_spec in self.base_path_specs:
            file_system = resolver.Resolver.OpenFileSystem(base_path_spec)
            file_entry = resolver.Resolver.OpenFileEntry(base_path_spec)     
            if file_entry is None:
                logging.warning(u'Unable to open base path specification:\n{0:s}'.format(base_path_spec.comparable))
            else:
                found = self._FileExists(curr, paths, file_entry, ignore_case)            
                if found:
                    return found
                continue
    def DirExists(self, dir_path):
        """Returns true if the provided path is a directory or false if not"""
        paths = dir_path.split('/')
        curr = 1
        for base_path_spec in self.base_path_specs:
            file_system = resolver.Resolver.OpenFileSystem(base_path_spec)
            file_entry = resolver.Resolver.OpenFileEntry(base_path_spec)     
            if file_entry is None:
                logging.warning(u'Unable to open base path specification:\n{0:s}'.format(base_path_spec.comparable))
            else:
                found = self._DirExists(curr, paths, file_entry)
                if found:
                    return found
                continue

    def SearchForFiles(self, file_name, path='/'):
        """Returns the path of all files with the given name, default search starts at root"""
        paths = path.split('/')
        curr = 1
        file_list = []
        for base_path_spec in self.base_path_specs:
            file_system = resolver.Resolver.OpenFileSystem(base_path_spec)
            file_entry = resolver.Resolver.OpenFileEntry(base_path_spec)     
            if file_entry is None:
                logging.warning(u'Unable to open base path specification:\n{0:s}'.format(base_path_spec.comparable))
            else:
                if path == '/' or path == '':
                    file_list.extend(self._SearchForFilesSub(file_name, file_entry, '/'))
                else:
                    file_list.extend(self._SearchForFiles(curr, paths, file_name, file_entry, '/'))
                
                continue
        if file_list:
            return file_list
        else:
            return None

    def SearchForDirs(self, dir_name, path='/'):
        """Returns the path of all directories with the given name, default search starts at root"""
        paths = path.split('/')
        curr = 1
        dir_list = []
        for base_path_spec in self.base_path_specs:
            file_system = resolver.Resolver.OpenFileSystem(base_path_spec)
            file_entry = resolver.Resolver.OpenFileEntry(base_path_spec)     
            if file_entry is None:
                logging.warning(u'Unable to open base path specification:\n{0:s}'.format(base_path_spec.comparable))
            else:
                if dir_name == '/' or dir_name == '':
                    return ['/']
                if path == '/' or path == '':
                    dir_list.extend(self._SearchForDirsSub(dir_name, file_entry, '/'))
                else:
                    dir_list.extend(self._SearchForDirs(curr, paths, dir_name, file_entry, '/'))
                continue
        if dir_list:
            return dir_list
        else:
            return None
    
    def _GetFile(self, curr, paths, file_entry, ignore_case):
        """Gets a file_object from a file_entry"""
        for sub_file_entry in file_entry.sub_file_entries:
            #if curr == (len(paths) - 1) and sub_file_entry.IsFile() and (sub_file_entry.name == paths[curr] 
            # or (ignore_case and sub_file_entry.name.lower() == paths[curr].lower())):
            #   file_object = sub_file_entry.GetFileObject()
            #   return    file_object
            if curr == (len(paths) - 1) and sub_file_entry.IsFile() and (sub_file_entry.name == paths[curr] 
             or (ignore_case and sub_file_entry.name.lower() == paths[curr].lower())):
                file_object = sub_file_entry.GetFileObject()
                return file_object
            if sub_file_entry.IsDirectory():
                if curr == (len(paths) - 1) and (sub_file_entry.name == paths[curr] or (ignore_case and sub_file_entry.name.lower() == paths[curr].lower())):
                    return sub_file_entry
                elif sub_file_entry.name == paths[curr] or (ignore_case and sub_file_entry.name.lower() == paths[curr].lower()):
                    return self._GetFile(curr + 1, paths, sub_file_entry, ignore_case)
        return None
   
    def ListRoot(self):
        dir_list = []
        for base_path_spec in self.base_path_specs:
            file_system = resolver.Resolver.OpenFileSystem(base_path_spec)
            file_entry = resolver.Resolver.OpenFileEntry(base_path_spec)     
            if file_entry is None:
                logging.warning(u'Unable to open base path specification:\n{0:s}'.format(base_path_spec.comparable))
            else:
                for sub_file_entry in file_entry.sub_file_entries:
                    dir_list.append(sub_file_entry.name)
                if dir_list is not None:
                    return dir_list
                continue

    def _ListDir(self, curr, paths, file_entry, recursive):
        """List the contents of the specified directory"""
        for sub_file_entry in file_entry.sub_file_entries:
            if curr == (len(paths) - 1) and sub_file_entry.IsDirectory() and sub_file_entry.name == paths[curr]:
                return self._ListDirSub(sub_file_entry, recursive)
            if sub_file_entry.IsDirectory():
                if sub_file_entry.name == paths[curr]:
                    return self._ListDir(curr + 1, paths, sub_file_entry, recursive)
        return []

    def _ListDirSub(self, file_entry, recursive, level=0):
        """Appends all contents of provided file_entry directory to list and returns list"""
        dir_list = []
        for sub_file_entry in file_entry.sub_file_entries:
            dir_list.append(sub_file_entry.name)
            if recursive and sub_file_entry.IsDirectory():
                dir_list.extend(_ListDirSub(file_entry, recursive, level + 1))
        return dir_list

    def _FileExists(self, curr, paths, file_entry, ignore_case):
        """Finds a file_object from a file_entry"""
        for sub_file_entry in file_entry.sub_file_entries:
            if curr == (len(paths) - 1) and sub_file_entry.IsFile() and (sub_file_entry.name == paths[curr] 
             or (ignore_case and sub_file_entry.name.lower() == paths[curr].lower())):
                return    True
            if sub_file_entry.IsDirectory() and curr < len(paths):
                if sub_file_entry.name == paths[curr] or (ignore_case and sub_file_entry.name.lower() == paths[curr].lower()):
                    return self._FileExists(curr + 1, paths, sub_file_entry, ignore_case)
        return False    

    def _DirExists(self, curr, paths, file_entry):
        """Returns True if directory is found in file_entry"""
        for sub_file_entry in file_entry.sub_file_entries:
            if curr == (len(paths) - 1) and sub_file_entry.IsDirectory() and sub_file_entry.name == paths[curr]:
                return True
            if sub_file_entry.IsDirectory() and curr < len(paths):
                if sub_file_entry.name == paths[curr]:
                    return self._DirExists(curr + 1, paths, sub_file_entry)
        return False

    def _SearchForFiles(self, curr, paths, file_name, file_entry, curr_path):
        """Gets the full path of the file being searched for"""
        for sub_file_entry in file_entry.sub_file_entries:
            if curr == (len(paths) - 1) and sub_file_entry.IsDirectory() and sub_file_entry.name == paths[curr]:
                return self._SearchForFilesSub(file_name, sub_file_entry, curr_path + sub_file_entry.name + '/')
            if sub_file_entry.IsDirectory() and sub_file_entry.name == paths[curr]:
                return self._SearchForFiles(curr + 1, paths, file_name, sub_file_entry, curr_path + sub_file_entry.name + '/')
        return None

    def _SearchForFilesSub(self, file_name, file_entry, curr_path):
        """Returns a list of all files with the file_name for every sub_file_entry"""
        file_list = []
        for sub_file_entry in file_entry.sub_file_entries:
            if sub_file_entry.IsFile() and sub_file_entry.name == file_name:
                file_list.append(curr_path + sub_file_entry.name)
            elif sub_file_entry.IsDirectory():
                file_list.extend(self._SearchForFilesSub(file_name, sub_file_entry, curr_path + sub_file_entry.name + '/'))

        return file_list    
    
    def _SearchForDirs(self, curr, paths, dir_name, file_entry, curr_path):
        """Gets the full path of the dir being searched for"""
        for sub_file_entry in file_entry.sub_file_entries:
            if curr == (len(paths) - 1) and sub_file_entry.IsDirectory() and sub_file_entry.name == paths[curr]:
                return self._SearchForDirsSub(dir_name, sub_file_entry, curr_path + sub_file_entry.name + '/')
            if sub_file_entry.IsDirectory() and sub_file_entry.name == paths[curr]:
                return self._SearchForDirs(curr + 1, paths, dir_name, sub_file_entry, curr_path + sub_file_entry.name + '/')
        return None

    def _SearchForDirsSub(self, dir_name, file_entry, curr_path):
        """Returns a list of all directories with the dir_name for every sub_file_entry"""
        dir_list = []
        for sub_file_entry in file_entry.sub_file_entries:
            if sub_file_entry.IsDirectory() and sub_file_entry.name == dir_name:
                dir_list.append(curr_path + sub_file_entry.name + '/')
            if sub_file_entry.IsDirectory():
                dir_list.extend(self._SearchForDirsSub(dir_name, sub_file_entry, curr_path + sub_file_entry.name + '/'))

        return dir_list    
    
    def _FormatHumanReadableSize(self, size):
        """Formats the size as a human readable string.
        Args:
            size: The size in bytes.
        Returns:
            A human readable string of the size.
        """
        magnitude_1000 = 0
        size_1000 = float(size)
        while size_1000 >= 1000:
            size_1000 /= 1000
            magnitude_1000 += 1

        magnitude_1024 = 0
        size_1024 = float(size)
        while size_1024 >= 1024:
            size_1024 /= 1024
            magnitude_1024 += 1

        size_string_1000 = None
        if magnitude_1000 > 0 and magnitude_1000 <= 7:
            size_string_1000 = u'{0:.1f}{1:s}'.format(
                    size_1000, self._UNITS_1000[magnitude_1000])

        size_string_1024 = None
        if magnitude_1024 > 0 and magnitude_1024 <= 7:
            size_string_1024 = u'{0:.1f}{1:s}'.format(
                    size_1024, self._UNITS_1024[magnitude_1024])

        if not size_string_1000 or not size_string_1024:
            return u'{0:d} B'.format(size)

        return u'{0:s} / {1:s} ({2:d} B)'.format(
                size_string_1024, size_string_1000, size)

    def _GetTSKPartitionIdentifiers(self, scan_node):
        """Determines the TSK partition identifiers.
        Args:
            scan_node: the scan node (instance of dfvfs.ScanNode).
        Returns:
            A list of partition identifiers.
        Raises:
            RuntimeError: if the format of or within the source is not supported or
                                        the the scan node is invalid or if the volume for
                                        a specific identifier cannot be retrieved.
        """
        if not scan_node or not scan_node.path_spec:
            raise RuntimeError(u'Invalid scan node.')

        volume_system = tsk_volume_system.TSKVolumeSystem()
        volume_system.Open(scan_node.path_spec)

        volume_identifiers = self._source_scanner.GetVolumeIdentifiers(
                volume_system)
        if not volume_identifiers:
            print(u'[WARNING] No partitions found.')
            return

        if len(volume_identifiers) == 1:
            return volume_identifiers

        try:
            selected_volume_identifier = self._PromptUserForPartitionIdentifier(
                    volume_system, volume_identifiers)
        except KeyboardInterrupt:
            raise RuntimeError(u'File system scan aborted.')

        if selected_volume_identifier == u'all':
            return volume_identifiers

        return [selected_volume_identifier]

    def _GetVSSStoreIdentifiers(self, scan_node):
        """Determines the VSS store identifiers.
        Args:
            scan_node: the scan node (instance of dfvfs.ScanNode).
        Returns:
            A list of VSS store identifiers.
        Raises:
            RuntimeError: if the format of or within the source
                                        is not supported or the the scan node is invalid.
        """
        if not scan_node or not scan_node.path_spec:
            raise RuntimeError(u'Invalid scan node.')

        volume_system = vshadow_volume_system.VShadowVolumeSystem()
        volume_system.Open(scan_node.path_spec)

        volume_identifiers = self._source_scanner.GetVolumeIdentifiers(
                volume_system)
        if not volume_identifiers:
            return []

        try:
            selected_store_identifiers = self._PromptUserForVSSStoreIdentifiers(
                    volume_system, volume_identifiers)
        except KeyboardInterrupt:
            raise errors.UserAbort(u'File system scan aborted.')

        return selected_store_identifiers

    def _ParseVSSStoresString(self, vss_stores):
        """Parses the user specified VSS stores string.
        A range of stores can be defined as: 3..5. Multiple stores can
        be defined as: 1,3,5 (a list of comma separated values). Ranges
        and lists can also be combined as: 1,3..5. The first store is 1.
        All stores can be defined as "all".
        Args:
            vss_stores: a string containing the VSS stores.
        Returns:
            A list containing the individual VSS stores numbers or the string "all".
        Raises:
            BadConfigOption: if the VSS stores option is invalid.
        """
        if not vss_stores:
            return []

        if vss_stores == u'all':
            return [u'all']

        stores = []
        for vss_store_range in vss_stores.split(u','):
            # Determine if the range is formatted as 1..3 otherwise it indicates
            # a single store number.
            if u'..' in vss_store_range:
                first_store, last_store = vss_store_range.split(u'..')
                try:
                    first_store = int(first_store, 10)
                    last_store = int(last_store, 10)
                except ValueError:
                    raise errors.BadConfigOption(
                            u'Invalid VSS store range: {0:s}.'.format(vss_store_range))

                for store_number in range(first_store, last_store + 1):
                    if store_number not in stores:
                        stores.append(store_number)
            else:
                if vss_store_range.startswith(u'vss'):
                    vss_store_range = vss_store_range[3:]

                try:
                    store_number = int(vss_store_range, 10)
                except ValueError:
                    raise errors.BadConfigOption(
                            u'Invalid VSS store range: {0:s}.'.format(vss_store_range))

                if store_number not in stores:
                    stores.append(store_number)

        return sorted(stores)

    def _PromptUserForEncryptedVolumeCredential(
            self, scan_context, locked_scan_node, credentials):
        """Prompts the user to provide a credential for an encrypted volume.
        Args:
            scan_context: the source scanner context (instance of
                                        SourceScannerContext).
            locked_scan_node: the locked scan node (instance of SourceScanNode).
            credentials: the credentials supported by the locked scan node (instance
                                     of dfvfs.Credentials).
        Returns:
            A boolean value indicating whether the volume was unlocked.
        """
        # TODO: print volume description.
        if locked_scan_node.type_indicator == definitions.TYPE_INDICATOR_BDE:
            print(u'Found a BitLocker encrypted volume.')
        else:
            print(u'Found an encrypted volume.')

        credentials_list = list(credentials.CREDENTIALS)
        credentials_list.append(u'skip')

        print(u'Supported credentials:')
        print(u'')
        for index, name in enumerate(credentials_list):
            print(u'    {0:d}. {1:s}'.format(index, name))
        print(u'')
        print(u'Note that you can abort with Ctrl^C.')
        print(u'')

        result = False
        while not result:
            print(u'Select a credential to unlock the volume: ', end=u'')
            # TODO: add an input reader.
            input_line = sys.stdin.readline()
            input_line = input_line.strip()

            if input_line in credentials_list:
                credential_type = input_line
            else:
                try:
                    credential_type = int(input_line, 10)
                    credential_type = credentials_list[credential_type]
                except (IndexError, ValueError):
                    print(u'Unsupported credential: {0:s}'.format(input_line))
                    continue

            if credential_type == u'skip':
                break

            credential_data = getpass.getpass(u'Enter credential data: ')
            print(u'')

            if credential_type == u'key':
                try:
                    credential_data = credential_data.decode(u'hex')
                except TypeError:
                    print(u'Unsupported credential data.')
                    continue

            result = self._source_scanner.Unlock(
                    scan_context, locked_scan_node.path_spec, credential_type,
                    credential_data)

            if not result:
                print(u'Unable to unlock volume.')
                print(u'')

        return result

    def _PromptUserForPartitionIdentifier(
            self, volume_system, volume_identifiers):
        """Prompts the user to provide a partition identifier.
        Args:
            volume_system: The volume system (instance of dfvfs.TSKVolumeSystem).
            volume_identifiers: List of allowed volume identifiers.
        Returns:
            A string containing the partition identifier or "all".
        Raises:
            FileSystemScannerError: if the source cannot be processed.
        """
        print(u'The following partitions were found:')
        print(u'Identifier\tOffset (in bytes)\tSize (in bytes)')

        for volume_identifier in sorted(volume_identifiers):
            volume = volume_system.GetVolumeByIdentifier(volume_identifier)
            if not volume:
                raise errors.FileSystemScannerError(
                        u'Volume missing for identifier: {0:s}.'.format(volume_identifier))

            volume_extent = volume.extents[0]
            print(u'{0:s}\t\t{1:d} (0x{1:08x})\t{2:s}'.format(
                    volume.identifier, volume_extent.offset,
                    self._FormatHumanReadableSize(volume_extent.size)))

        while True:
            print(
                    u'Please specify the identifier of the partition that should be '
                    u'processed.')
            print(
                    u'All partitions can be defined as: "all". Note that you '
                    u'can abort with Ctrl^C.')

            selected_volume_identifier = sys.stdin.readline()
            selected_volume_identifier = selected_volume_identifier.strip()

            if not selected_volume_identifier.startswith(u'p'):
                try:
                    partition_number = int(selected_volume_identifier, 10)
                    selected_volume_identifier = u'p{0:d}'.format(partition_number)
                except ValueError:
                    pass

            if (selected_volume_identifier == u'all' or
                    selected_volume_identifier in volume_identifiers):
                break

            print(u'')
            print(
                    u'Unsupported partition identifier, please try again or abort '
                    u'with Ctrl^C.')
            print(u'')

        return selected_volume_identifier

    def _PromptUserForVSSStoreIdentifiers(
            self, volume_system, volume_identifiers):
        """Prompts the user to provide the VSS store identifiers.
        This method first checks for the preferred VSS stores and falls back
        to prompt the user if no usable preferences were specified.
        Args:
            volume_system: The volume system (instance of dfvfs.VShadowVolumeSystem).
            volume_identifiers: List of allowed volume identifiers.
        Returns:
            The list of selected VSS store identifiers or None.
        Raises:
            SourceScannerError: if the source cannot be processed.
        """
        normalized_volume_identifiers = []
        for volume_identifier in volume_identifiers:
            volume = volume_system.GetVolumeByIdentifier(volume_identifier)
            if not volume:
                raise errors.SourceScannerError(
                        u'Volume missing for identifier: {0:s}.'.format(volume_identifier))

            try:
                volume_identifier = int(volume.identifier[3:], 10)
                normalized_volume_identifiers.append(volume_identifier)
            except ValueError:
                pass

        print_header = True
        while True:
            if print_header:
                print(u'The following Volume Shadow Snapshots (VSS) were found:')
                print(u'Identifier\tVSS store identifier')

                for volume_identifier in volume_identifiers:
                    volume = volume_system.GetVolumeByIdentifier(volume_identifier)
                    if not volume:
                        raise errors.SourceScannerError(
                                u'Volume missing for identifier: {0:s}.'.format(
                                        volume_identifier))

                    vss_identifier = volume.GetAttribute(u'identifier')
                    print(u'{0:s}\t\t{1:s}'.format(
                            volume.identifier, vss_identifier.value))

                print(u'')

                print_header = False

            print(
                    u'Please specify the identifier(s) of the VSS that should be '
                    u'processed:')
            print(
                    u'Note that a range of stores can be defined as: 3..5. Multiple '
                    u'stores can')
            print(
                    u'be defined as: 1,3,5 (a list of comma separated values). Ranges '
                    u'and lists can')
            print(
                    u'also be combined as: 1,3..5. The first store is 1. All stores '
                    u'can be defined')
            print(u'as "all". If no stores are specified none will be processed. You')
            print(u'can abort with Ctrl^C.')

            selected_vss_stores = sys.stdin.readline()

            selected_vss_stores = selected_vss_stores.strip()
            if not selected_vss_stores:
                break

            try:
                selected_vss_stores = self._ParseVSSStoresString(selected_vss_stores)
            except errors.BadConfigOption:
                selected_vss_stores = []

            if selected_vss_stores == [u'all']:
                # We need to set the stores to cover all vss stores.
                selected_vss_stores = range(1, volume_system.number_of_volumes + 1)

            if not set(selected_vss_stores).difference(normalized_volume_identifiers):
                break

            print(u'')
            print(
                    u'Unsupported VSS identifier(s), please try again or abort with '
                    u'Ctrl^C.')
            print(u'')

        return selected_vss_stores

    def _ScanVolume(self, scan_context, volume_scan_node, base_path_specs):
        """Scans the volume scan node for volume and file systems.
        Args:
            scan_context: the source scanner context (instance of
                                        SourceScannerContext).
            volume_scan_node: the volume scan node (instance of dfvfs.ScanNode).
            base_path_specs: a list of source path specification (instances
                                             of dfvfs.PathSpec).
        Raises:
            RuntimeError: if the format of or within the source
                                        is not supported or the the scan node is invalid.
        """
        if not volume_scan_node or not volume_scan_node.path_spec:
            raise RuntimeError(u'Invalid or missing volume scan node.')

        if len(volume_scan_node.sub_nodes) == 0:
            self._ScanVolumeScanNode(scan_context, volume_scan_node, base_path_specs)

        else:
            # Some volumes contain other volume or file systems e.g. BitLocker ToGo
            # has an encrypted and unencrypted volume.
            for sub_scan_node in volume_scan_node.sub_nodes:
                self._ScanVolumeScanNode(scan_context, sub_scan_node, base_path_specs)

    def _ScanVolumeScanNode(
            self, scan_context, volume_scan_node, base_path_specs):
        """Scans an individual volume scan node for volume and file systems.
        Args:
            scan_context: the source scanner context (instance of
                                        SourceScannerContext).
            volume_scan_node: the volume scan node (instance of dfvfs.ScanNode).
            base_path_specs: a list of source path specification (instances
                                             of dfvfs.PathSpec).
        Raises:
            RuntimeError: if the format of or within the source
                                        is not supported or the the scan node is invalid.
        """
        if not volume_scan_node or not volume_scan_node.path_spec:
            raise RuntimeError(u'Invalid or missing volume scan node.')

        # Get the first node where where we need to decide what to process.
        scan_node = volume_scan_node
        while len(scan_node.sub_nodes) == 1:
            scan_node = scan_node.sub_nodes[0]

        # The source scanner found an encrypted volume and we need
        # a credential to unlock the volume.
        if scan_node.type_indicator in definitions.ENCRYPTED_VOLUME_TYPE_INDICATORS:
            self._ScanVolumeScanNodeEncrypted(
                    scan_context, scan_node, base_path_specs)

        elif scan_node.type_indicator == definitions.TYPE_INDICATOR_VSHADOW:
            self._ScanVolumeScanNodeVSS(scan_context, scan_node, base_path_specs)

        elif scan_node.type_indicator in definitions.FILE_SYSTEM_TYPE_INDICATORS:
            base_path_specs.append(scan_node.path_spec)

    def _ScanVolumeScanNodeEncrypted(
            self, scan_context, volume_scan_node, base_path_specs):
        """Scans an encrypted volume scan node for volume and file systems.
        Args:
            scan_context: the source scanner context (instance of
                                        SourceScannerContext).
            volume_scan_node: the volume scan node (instance of dfvfs.ScanNode).
            base_path_specs: a list of source path specification (instances
                                             of dfvfs.PathSpec).
        """
        result = not scan_context.IsLockedScanNode(volume_scan_node.path_spec)
        if not result:
            credentials = credentials_manager.CredentialsManager.GetCredentials(
                    volume_scan_node.path_spec)

            result = self._PromptUserForEncryptedVolumeCredential(
                    scan_context, volume_scan_node, credentials)

        if result:
            self._source_scanner.Scan(
                    scan_context, scan_path_spec=volume_scan_node.path_spec)
            self._ScanVolume(scan_context, volume_scan_node, base_path_specs)

    def _ScanVolumeScanNodeVSS(
            self, scan_context, volume_scan_node, base_path_specs):
        """Scans a VSS volume scan node for volume and file systems.
        Args:
            scan_context: the source scanner context (instance of
                                        SourceScannerContext).
            volume_scan_node: the volume scan node (instance of dfvfs.ScanNode).
            base_path_specs: a list of source path specification (instances
                                             of dfvfs.PathSpec).
        Raises:
            SourceScannerError: if a VSS sub scan node scannot be retrieved.
        """
        vss_store_identifiers = self._GetVSSStoreIdentifiers(volume_scan_node)

        self._vss_stores = list(vss_store_identifiers)

        # Process VSS stores starting with the most recent one.
        vss_store_identifiers.reverse()
        for vss_store_identifier in vss_store_identifiers:
            location = u'/vss{0:d}'.format(vss_store_identifier)
            sub_scan_node = volume_scan_node.GetSubNodeByLocation(location)
            if not sub_scan_node:
                raise errors.SourceScannerError(
                        u'Scan node missing for VSS store identifier: {0:d}.'.format(
                                vss_store_identifier))

            self._source_scanner.Scan(
                    scan_context, scan_path_spec=sub_scan_node.path_spec)
            self._ScanVolume(scan_context, sub_scan_node, base_path_specs)

    def GetBasePathSpecs(self, source_path):
        """Determines the base path specifications.
        Args:
            source_path: the source path.
        Returns:
            A list of path specifications (instances of dfvfs.PathSpec).
        Raises:
            RuntimeError: if the source path does not exists, or if the source path
                                        is not a file or directory, or if the format of or within
                                        the source file is not supported.
        """
        if (not source_path.startswith(u'\\\\.\\') and
                not os.path.exists(source_path)):
            raise RuntimeError(
                    u'No such device, file or directory: {0:s}.'.format(source_path))

        scan_context = source_scanner.SourceScannerContext()
        scan_context.OpenSourcePath(source_path)

        try:
            self._source_scanner.Scan(scan_context)
        except (errors.BackEndError, ValueError) as exception:
            raise RuntimeError(
                    u'Unable to scan source with error: {0:s}.'.format(exception))

        if scan_context.source_type not in [
                definitions.SOURCE_TYPE_STORAGE_MEDIA_DEVICE,
                definitions.SOURCE_TYPE_STORAGE_MEDIA_IMAGE]:
            scan_node = scan_context.GetRootScanNode()
            return [scan_node.path_spec]

        # Get the first node where where we need to decide what to process.
        scan_node = scan_context.GetRootScanNode()
        while len(scan_node.sub_nodes) == 1:
            scan_node = scan_node.sub_nodes[0]

        # The source scanner found a partition table and we need to determine
        # which partition needs to be processed.
        if scan_node.type_indicator != definitions.TYPE_INDICATOR_TSK_PARTITION:
            partition_identifiers = None

        else:
            partition_identifiers = self._GetTSKPartitionIdentifiers(scan_node)

        base_path_specs = []
        if not partition_identifiers:
            self._ScanVolume(scan_context, scan_node, base_path_specs)

        else:
            for partition_identifier in partition_identifiers:
                location = u'/{0:s}'.format(partition_identifier)
                sub_scan_node = scan_node.GetSubNodeByLocation(location)
                self._ScanVolume(scan_context, sub_scan_node, base_path_specs)

        if not base_path_specs:
            raise RuntimeError(
                    u'No supported file system found in source.')

        return base_path_specs

def Main():
    logging.basicConfig(
            level=logging.INFO, format=u'[%(levelname)s] %(message)s')

    return_value = True
    #dfvfs_util = DfvfsUtil("/mnt/ewf_mount1/ewf1")
    dfvfs_util = DfvfsUtil("/media/sf_Forensics/Training/SANS508/xp-tdungan-10.3.58.7/xp-tdungan-c-drive/xp-tdungan-c-drive.E01")  

    try:
        #TEST GET FILE
        my_file = dfvfs_util.GetFile("/WINDOWS")
        print(my_file.__dict__)
        directory_entry = my_file._tsk_file
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
            file_type = str(directory_entry.info.meta.type)
            inode = str(directory_entry.info.meta.addr)
            mod = str(directory_entry.info.meta.mtime)
            acc = str(directory_entry.info.meta.atime)
            chg = str(directory_entry.info.meta.ctime)
            cre = str(directory_entry.info.meta.crtime)
            size = str(directory_entry.info.meta.size)
            uid = str(directory_entry.info.meta.uid)
            gid = str(directory_entry.info.meta.gid)
        print ("File Type: " + file_type + " | inode: " + inode + " | mod: " + mod + " | acc: " + acc + " | chg: " + chg + " | cre: " + cre + " | size: " + size + " | uid: " + uid + " | gid: " + gid)
        if my_file is not None:
            print("1 Success for GetFile(/Windows/System32/Drivers/etc/hosts)")
        else:
            print("1 Failed for GetFile")

        output = dfvfs_util.ListDir("/WINDOWS/")
        print("\n\t".join(output))
        sys.exit(1)

        #TEST GET FILE with IGNORE CASE
        my_file = dfvfs_util.GetFile("/windows/SYSTEM32/dRiVeRs/eTc/HOSTs", True)
        if my_file is not None:
            print("2 Success for GetFile Ignore Case")
        else:
            print("2 Failed for GetFile Ignore Case")
        
        #TEST LIST DIR
        dir_list = dfvfs_util.ListDir("/")
        if dir_list is not None:
            print("\n\t".join(dir_list))
            print("3 Success for ListDir")
        else:
            print("3 Failed for ListDir")        

        #TEST FILE EXISTS true
        found = dfvfs_util.FileExists("/WINDOWS/system32/drivers/etc/hosts")
        if found:
            print("4 Success for FileExists")
        else:
            print("4 Failed for FileExists")
        
        #TEST FILE EXISTS false
        found = dfvfs_util.FileExists("/WINDOWS/system32/drivers/etc/hoss")
        if not found:
            print("5 Success for FileExists")
        else:
            print("5 Failed for FileExists")

        #TEST DIR EXISTS true
        found = dfvfs_util.DirExists("/WINDOWS/system32/drivers")
        if found:
            print("6 Success for DirExists")
        else:
            print("6 Failed for DirExists")

        #TEST DIR EXISTS false
        found = dfvfs_util.DirExists("/WINDOWS/system32/et")
        if not found:
            print("7 Success for FileExists")
        else:
            print("7 Failed for FileExists")

        #TEST SEARCH FOR FILES true
        found = dfvfs_util.SearchForFiles('hosts', '/WINDOWS/system32/drivers')
        if found:
            print("\n\t".join(found))
            print("8 Success for search for files")
        else:
            print("8 Failed for search for files")

        #TEST SEARCH FOR DIRS true
        found = dfvfs_util.SearchForDirs('drivers', '/WINDOWS')
        if found:
            print("\n\t".join(found))
            print("9 Success for search for directories")
        else:
            print("9 Failed for search for directories")
        
        #TEST ICAT
        pwd = os.path.dirname(os.path.realpath(__file__))
        dfvfs_util.Icat("/WINDOWS/system32/drivers/etc/hosts", pwd + "/hosts")

        print(u'')
        print(u'Completed.')

    except KeyboardInterrupt:
        return_value = False

        print(u'')
        print(u'Aborted by user.')

    return return_value


if __name__ == '__main__':
    sys.exit(0)
    if not Main():
        sys.exit(1)
    else:
        sys.exit(0)
