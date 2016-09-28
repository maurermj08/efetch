#!/usr/bin/python
# TODO: Require vftools as a dependency and not use a seperate dfvfs_util
# -*- coding: utf-8 -*-
"""Simple utility for getting files and information from dfvfs."""

# This code is similar recursive_hasher example found on dfvfs github
#  at https://github.com/log2timeline/dfvfs/
#  This code is based on code by Joachim Metz

from __future__ import print_function
import datetime
import getpass
import jinja2
import logging
import os
import pytz
import sys

from dfvfs.credentials import manager as credentials_manager
from dfvfs.helpers import source_scanner
from dfvfs.lib import definitions
from dfvfs.lib import errors
from dfvfs.resolver import resolver
from dfvfs.volume import tsk_volume_system
from dfvfs.volume import vshadow_volume_system
from dfvfs.serializer.json_serializer import JsonPathSpecSerializer


class DfvfsUtil(object):
    """Class that provides a simple interface into dfvfs."""

    # Class constant that defines the default read buffer size.
    _READ_BUFFER_SIZE = 32768

    # For context see: http://en.wikipedia.org/wiki/Byte
    _UNITS_1000 = [u'B', u'kB', u'MB', u'GB', u'TB', u'EB', u'ZB', u'YB']
    _UNITS_1024 = [u'B', u'KiB', u'MiB', u'GiB', u'TiB', u'EiB', u'ZiB', u'YiB']

    base_path_specs = None
    settings = None
    options = []
    display = ''
    initialized = 0

    def __init__(self, source=None, settings=[u'all',u'all',u'all',u'all'], interactive=True, is_pathspec=False):
        """Initializes the dfvfs util object."""
        super(DfvfsUtil, self).__init__()
        self._source_scanner = source_scanner.SourceScanner()
        self.settings = settings
        self.env = jinja2.Environment()
        self.env.filters['datetime'] = self.format_datetime

        if source and not is_pathspec:
            self.base_path_specs = self.get_base_pathspecs(source, interactive)
        elif source and is_pathspec:
            self.base_path_specs = self.get_base_from_pathspec(source, interactive)

    def export_file(self, pathspec, output_path=None):
        """Outputs a pathspec to the specified path"""
        file_entry = resolver.Resolver.OpenFileEntry(pathspec)
        in_file = file_entry.GetFileObject()
        if output_path:
            output = open(output_path, "wb")
        else:
            output = sys.stdout
        data = in_file.read(32768)

        while data:
            output.write(data)
            data = in_file.read(32768)

        if output_path:
            output.close()

    def decode_pathspec(self, encoded_pathspec):
        return JsonPathSpecSerializer.ReadSerialized(encoded_pathspec)

    def encode_pathspec(self, pathspec):
        return JsonPathSpecSerializer.WriteSerialized(pathspec)

    def encode_pathspecs(self, pathspec):
        if isinstance(pathspec, list):
            pathspecs = []
            for spec in pathspec:
                pathspecs.append(self.encode_pathspec(spec))
            return pathspecs

        return self.encode_pathspec(pathspec)

    def get_pathspec_basic_information(self, pathspec):
        """Creates a dictionary of basic information about the pathspec without opening the file"""
        pathspec_information = {}
        pathspec_information['pathspec'] = self.encode_pathspec(pathspec)

        pathspec_information['path'] = pathspec.location
        pathspec_information['type_indicator'] = pathspec.type_indicator
        if pathspec_information['type_indicator'] == 'TSK':
            pathspec_information['inode'] = pathspec.inode
        pathspec_information['file_name'] = os.path.basename(pathspec_information['path'])
        pathspec_information['dir'] = os.path.dirname(pathspec_information['path'])
        pathspec_information['ext'] = os.path.splitext(pathspec_information['file_name'])[1][1:].lower() or ""

        return pathspec_information

    def get_pathspec_information(self, pathspec):
        """Creates a dictionary of information about the pathspec, must open the file in memory"""
        pathspec_information = self.get_pathspec_basic_information(pathspec)
        file_entry = resolver.Resolver.OpenFileEntry(pathspec)

        stat_object = file_entry.GetStat()

        for attribute in [ 'mtime', 'atime', 'ctime', 'crtime', 'size', 'mode', 'uid', 'gid']:
            pathspec_information[attribute] = str(getattr(stat_object, attribute, ''))

        pathspec_information['inode'] = getattr(stat_object, 'ino', '')

        type = getattr(stat_object, 'type', '')
        if type:
            if type == definitions.FILE_ENTRY_TYPE_DEVICE:
                pathspec_information['type'] = 'device'
                pathspec_information['legacy_type'] = 'b/b'
            if type == definitions.FILE_ENTRY_TYPE_DIRECTORY:
                pathspec_information['type'] = 'dir'
                pathspec_information['legacy_type'] = 'd/d'
            if type == definitions.FILE_ENTRY_TYPE_FILE:
                pathspec_information['type'] = 'file'
                pathspec_information['legacy_type'] = 'r/r'
            if type == definitions.FILE_ENTRY_TYPE_LINK:
                pathspec_information['type'] = 'link'
                pathspec_information['legacy_type'] = 'l/l'
            if type == definitions.FILE_ENTRY_TYPE_SOCKET:
                pathspec_information['type'] = 'socket'
                pathspec_information['legacy_type'] = 'h/h'
            if type == definitions.FILE_ENTRY_TYPE_PIPE:
                pathspec_information['type'] = 'pipe'
                pathspec_information['legacy_type'] = 'p/p'

        return  pathspec_information

    def list_directory(self, pathspec=None, recursive=False, display=False,
                       show_pathspec=True, information=False, display_root=True, jinja_format=None):
        """Lists a directory using a pathspec or list of pathspecs"""
        directory_list = []

        if not pathspec:
            pathspec = self.base_path_specs
        if not isinstance(pathspec, list):
            pathspec = [pathspec]
        for individual_pathspec in pathspec:
            directory_list.extend(self._list_directory(resolver.Resolver.OpenFileEntry(individual_pathspec),recursive,
                                                       display, 0, show_pathspec, information, display_root,
                                                       jinja_format))

        return directory_list

    def _list_directory(self, file_entry, recursive=False, display=False, depth=0,
                        show_pathspec=True, information=False, display_root=False, jinja_format=None):
        """Lists a directory using a file entry"""
        directory_list = []
        if information:
            directory_list.append(self.get_pathspec_information(file_entry.path_spec))
        else:
            directory_list.append(file_entry.name)

        if display:
            self._print_file_entry(file_entry, depth, show_pathspec, display_root, jinja_format)

        if (recursive or depth == 0) and file_entry.IsDirectory():
            for sub_file_entry in file_entry.sub_file_entries:
                directory_list.extend(self._list_directory(sub_file_entry, recursive, display, depth + 1, show_pathspec,
                                                           information, display_root, jinja_format))

        return directory_list

    def print_pathspec(self, pathspec=None, display_root=True, jinja_format=None):
        """Prints one or more pathspecs to standard out"""
        if not pathspec:
            pathspec = self.base_path_specs
        if not isinstance(pathspec, list):
            pathspec = [pathspec]
        for individual_pathspec in pathspec:
            self._print_file_entry(resolver.Resolver.OpenFileEntry(individual_pathspec), display_root=display_root,
                                   jinja_format=jinja_format)

    def format_datetime(self, epoch, timezone=None):
        """Converts epoch time in seconds to ISO standard"""
        if timezone:
            timezone = pytz.timezone(timezone)

        if isinstance(epoch, str) and not epoch:
            epoch = 0

        return datetime.datetime.fromtimestamp(float(epoch), timezone).isoformat()

    def _print_file_entry(self, file_entry, depth=0, show_pathspec=True, display_root=True,
                          jinja_format='{{name}}\t{{pathspec}}'):
        """Prints a file entry to standard out """
        if not display_root and depth == 0:
            return
        elif not display_root:
            depth -= 1

        if not jinja_format:
            jinja_format = '{{name}}\t{{pathspec}}'

        template = self.env.from_string(jinja_format)
        information = self.get_pathspec_information(file_entry.path_spec)

        # Adds a padded file_name to pretty print results
        information['padded_file_name'] = information['file_name'] + \
                                          (' ' * max(0, 32 - len(information['file_name'])))

        # Gets the file_name, setting root to '/' or path_spec parent location
        information['name'] = file_entry.name
        if depth == 0 and not information['name']:
            if hasattr(file_entry.path_spec.parent, 'location'):
                information['name'] = file_entry.path_spec.parent.location
            else:
                information['name'] = '/'
        if depth == 0 and not information['name']:
            if hasattr(file_entry.path_spec.parent, 'location'):
                information['name'] = file_entry.path_spec.parent.location
            else:
                information['name'] = '/'

        # Gives the options of setting depth like in sleuthkit
        information['depth'] = '+' * depth

        information['legacy_type'] = ''
        if information['type'] == 'dir':
            information['legacy_type'] = 'd/d'
        else:
            information['legacy_type'] = 'r/r'

        print(template.render(information))

    def _format_human_readable_size(self, size):
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

    def _get_tsk_partition_identifiers(self, scan_node, interactive):
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

        # TODO REMOVE INTERACTION
        # try:
        #     selected_volume_identifier = self._prompt_user_for_partition_identifier(
        #         volume_system, volume_identifiers, interactive)
        # except KeyboardInterrupt:
        #     raise RuntimeError(u'File system scan aborted.')
        #
        # if selected_volume_identifier == u'all':
        return volume_identifiers

        # return [selected_volume_identifier]

    def _get_vss_store_identifiers(self, scan_node, interactive):
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
            selected_store_identifiers = self._prompt_user_for_vss_store_identifiers(
                volume_system, volume_identifiers, interactive)
        except KeyboardInterrupt:
            raise errors.UserAbort(u'File system scan aborted.')

        return selected_store_identifiers

    def _parse_vss_stores_string(self, vss_stores):
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

        #if vss_stores == u'all':
        return [u'all']
        #
        # stores = []
        # for vss_store_range in vss_stores.split(u','):
        #     # Determine if the range is formatted as 1..3 otherwise it indicates
        #     # a single store number.
        #     if u'..' in vss_store_range:
        #         first_store, last_store = vss_store_range.split(u'..')
        #         try:
        #             first_store = int(first_store, 10)
        #             last_store = int(last_store, 10)
        #         except ValueError:
        #             raise errors.BadConfigOption(
        #                 u'Invalid VSS store range: {0:s}.'.format(vss_store_range))
        #
        #         for store_number in range(first_store, last_store + 1):
        #             if store_number not in stores:
        #                 stores.append(store_number)
        #     else:
        #         if vss_store_range.startswith(u'vss'):
        #             vss_store_range = vss_store_range[3:]
        #
        #         try:
        #             store_number = int(vss_store_range, 10)
        #         except ValueError:
        #             raise errors.BadConfigOption(
        #                 u'Invalid VSS store range: {0:s}.'.format(vss_store_range))
        #
        #         if store_number not in stores:
        #             stores.append(store_number)
        #
        # return sorted(stores)

    def _prompt_user_for_encrypted_volume_credential(
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
            self.settings.append(input_line.strip())
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

    def _prompt_user_for_partition_identifier(
            self, volume_system, volume_identifiers, interactive):
        """Prompts the user to provide a partition identifier.
        Args:
            volume_system: The volume system (instance of dfvfs.TSKVolumeSystem).
            volume_identifiers: List of allowed volume identifiers.
        Returns:
            A string containing the partition identifier or "all".
        Raises:
            FileSystemScannerError: if the source cannot be processed.
        """
        if interactive:
            print(u'The following partitions were found:')
            print(u'Identifier\tOffset (in bytes)\tSize (in bytes)')
        else:
            self.display = u'The following partitions were found: \nIdentifier\tOffset (in bytes)\tSize (in bytes)\n'

        for volume_identifier in sorted(volume_identifiers):
            volume = volume_system.GetVolumeByIdentifier(volume_identifier)
            if not volume:
                raise errors.FileSystemScannerError(
                    u'Volume missing for identifier: {0:s}.'.format(volume_identifier))

            volume_extent = volume.extents[0]
            if interactive:
                print(u'{0:s}\t\t{1:d} (0x{1:08x})\t{2:s}'.format(
                    volume.identifier, volume_extent.offset,
                    self._format_human_readable_size(volume_extent.size)))
            else:
                self.display += u'{0:s}\t\t{1:d} (0x{1:08x})\t{2:s}\n'.format(
                    volume.identifier, volume_extent.offset,
                    self._format_human_readable_size(volume_extent.size))

        # while True:
        #     if interactive:
        #         print(
        #             u'Please specify the identifier of the partition that should be '
        #             u'processed.')
        #         print(
        #             u'All partitions can be defined as: "all". Note that you '
        #             u'can abort with Ctrl^C.')
        #
        #         selected_volume_identifier = sys.stdin.readline()
        #         self.settings.append(selected_volume_identifier.strip())
        #         selected_volume_identifier = selected_volume_identifier.strip()
        #     else:
        #         if not self.settings:
        #             self.options = sorted(volume_identifiers)
        #             self.initialized = -1
        #             return
        #         else:
        #             selected_volume_identifier = self.settings.pop(0)
        #
        #     if not selected_volume_identifier.startswith(u'p'):
        #         try:
        #             partition_number = int(selected_volume_identifier, 10)
        #             selected_volume_identifier = u'p{0:d}'.format(partition_number)
        #         except ValueError:
        #             pass
        #
        #     if (selected_volume_identifier == u'all' or
        #                 selected_volume_identifier in volume_identifiers):
        #         break
        #
        #     if interactive:
        #         print(u'')
        #         print(
        #             u'Unsupported partition identifier, please try again or abort '
        #             u'with Ctrl^C.')
        #         print(u'')

        return u'all'

    def _prompt_user_for_vss_store_identifiers(
            self, volume_system, volume_identifiers, interactive):
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

        return range(1, volume_system.number_of_volumes + 1)

        # print_header = True
        # while True:
        #     if interactive:
        #         if print_header:
        #             print(u'The following Volume Shadow Snapshots (VSS) were found:')
        #             print(u'Identifier\tVSS store identifier')
        #
        #             for volume_identifier in volume_identifiers:
        #                 volume = volume_system.GetVolumeByIdentifier(volume_identifier)
        #                 if not volume:
        #                     raise errors.SourceScannerError(
        #                         u'Volume missing for identifier: {0:s}.'.format(
        #                             volume_identifier))
        #
        #                 vss_identifier = volume.GetAttribute(u'identifier')
        #                 print(u'{0:s}\t\t{1:s}'.format(
        #                     volume.identifier, vss_identifier.value))
        #
        #             print(u'')
        #
        #             print_header = False
        #
        #         print(
        #             u'Please specify the identifier(s) of the VSS that should be '
        #             u'processed:')
        #         print(
        #             u'Note that a range of stores can be defined as: 3..5. Multiple '
        #             u'stores can')
        #         print(
        #             u'be defined as: 1,3,5 (a list of comma separated values). Ranges '
        #             u'and lists can')
        #         print(
        #             u'also be combined as: 1,3..5. The first store is 1. All stores '
        #             u'can be defined')
        #         print(u'as "all". If no stores are specified none will be processed. You')
        #         print(u'can abort with Ctrl^C.')
        #
        #         selected_vss_stores = sys.stdin.readline()
        #         self.settings.append(selected_vss_stores.strip())
        #     else:
        #         self.display = u'The following Volume Shadow Snapshots (VSS) were found:\nTo add evidence without any snapshots use "none"\nIdentifier\tVSS store identifier\n'
        #         self.options = ['none']
        #
        #         for volume_identifier in volume_identifiers:
        #             volume = volume_system.GetVolumeByIdentifier(volume_identifier)
        #             if not volume:
        #                 raise errors.SourceScannerError(
        #                     u'Volume missing for identifier: {0:s}.'.format(
        #                         volume_identifier))
        #
        #             vss_identifier = volume.GetAttribute(u'identifier')
        #             self.display += u'{0:s}\t\t{1:s}\n'.format(volume.identifier, vss_identifier.value)
        #             self.options.append(volume.identifier)
        #         if self.settings:
        #             selected_vss_stores = self.settings.pop(0)
        #             if str(selected_vss_stores).lower() == 'none':
        #                 selected_vss_stores = []
        #         else:
        #             self.initialized = -1
        #             return
        #
        #     if not selected_vss_stores:
        #         break
        #
        #     selected_vss_stores = selected_vss_stores.strip()
        #
        #     try:
        #         selected_vss_stores = self._parse_vss_stores_string(selected_vss_stores)
        #     except errors.BadConfigOption:
        #         selected_vss_stores = []
        #
        #     if selected_vss_stores == [u'all']:
        #         # We need to set the stores to cover all vss stores.
        #         selected_vss_stores = range(1, volume_system.number_of_volumes + 1)
        #
        #     if not set(selected_vss_stores).difference(normalized_volume_identifiers):
        #         break
        #
        #     print(u'')
        #     print(
        #         u'Unsupported VSS identifier(s), please try again or abort with '
        #         u'Ctrl^C.')
        #     print(u'')
        #
        # return selected_vss_stores

    def _scan_volume(self, scan_context, volume_scan_node, base_path_specs, interactive):
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
            self._scan_volume_scan_node(scan_context, volume_scan_node, base_path_specs, interactive)

        else:
            # Some volumes contain other volume or file systems e.g. BitLocker ToGo
            # has an encrypted and unencrypted volume.
            for sub_scan_node in volume_scan_node.sub_nodes:
                self._scan_volume_scan_node(scan_context, sub_scan_node, base_path_specs, interactive)
                if self.initialized < 0:
                    return

    def _scan_volume_scan_node(
            self, scan_context, volume_scan_node, base_path_specs, interactive):
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
            self._scan_volume_scan_node_encrypted(
                scan_context, scan_node, base_path_specs, interactive)

        elif scan_node.type_indicator == definitions.TYPE_INDICATOR_VSHADOW:
            self._scan_volume_scan_node_vss(scan_context, scan_node, base_path_specs, interactive)

        elif scan_node.type_indicator in definitions.FILE_SYSTEM_TYPE_INDICATORS:
            base_path_specs.append(scan_node.path_spec)

    def _scan_volume_scan_node_encrypted(
            self, scan_context, volume_scan_node, base_path_specs, interactive):
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

            result = self._prompt_user_for_encrypted_volume_credential(
                scan_context, volume_scan_node, credentials, interactive)

        if result:
            self._source_scanner.Scan(
                scan_context, scan_path_spec=volume_scan_node.path_spec)
            self._scan_volume(scan_context, volume_scan_node, base_path_specs, interactive)

    def _scan_volume_scan_node_vss(
            self, scan_context, volume_scan_node, base_path_specs, interactive):
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
        vss_store_identifiers = self._get_vss_store_identifiers(volume_scan_node, interactive)

        if self.initialized < 0:
            return

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
            self._scan_volume(scan_context, sub_scan_node, base_path_specs, interactive)

    def get_base_from_pathspec(self, source_pathspec, interactive):
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
        self.initialized = 0

        # if (not source_path.startswith(u'\\\\.\\') and
        #         not os.path.exists(source_path)):
        #     raise RuntimeError(
        #         u'No such device, file or directory: {0:s}.'.format(source_path))

        scan_context = source_scanner.SourceScannerContext()
        #scan_context.OpenSourcePath(source_path) # TODO Does self.AddScanNode(source_path_spec, None)
        scan_context.AddScanNode(source_pathspec, None)

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
        #TODO The root_path_spec is the actual os pathspec of the evidence item (or any pathspec for that matter)
        print('HERE' + str(JsonPathSpecSerializer.WriteSerialized(scan_context._root_path_spec))) #TODO DING DING DING
        print('')
        while len(scan_node.sub_nodes) == 1:
            scan_node = scan_node.sub_nodes[0]

        # The source scanner found a partition table and we need to determine
        # which partition needs to be processed.
        if scan_node.type_indicator != definitions.TYPE_INDICATOR_TSK_PARTITION:
            partition_identifiers = None
        else:
            partition_identifiers = self._get_tsk_partition_identifiers(scan_node, interactive)

        if self.initialized < 0:
            return

        base_path_specs = []
        if not partition_identifiers:
            self._scan_volume(scan_context, scan_node, base_path_specs, interactive)
        else:
            for partition_identifier in partition_identifiers:
                location = u'/{0:s}'.format(partition_identifier)
                sub_scan_node = scan_node.GetSubNodeByLocation(location)
                self._scan_volume(scan_context, sub_scan_node, base_path_specs, interactive)

        if self.initialized < 0:
            return
        else:
            self.initialized = 1

        if not base_path_specs:
            raise RuntimeError(
                u'No supported file system found in source.')

        return base_path_specs

    def get_base_pathspecs(self, source_path, interactive):
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
        self.initialized = 0

        if (not source_path.startswith(u'\\\\.\\') and
                not os.path.exists(source_path)):
            raise RuntimeError(
                u'No such device, file or directory: {0:s}.'.format(source_path))

        scan_context = source_scanner.SourceScannerContext()
        scan_context.OpenSourcePath(source_path) # TODO Does self.AddScanNode(source_path_spec, None)

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
        #TODO The root_path_spec is the actual os pathspec of the evidence item (or any pathspec for that matter)
        print('HERE' + str(JsonPathSpecSerializer.WriteSerialized(scan_context._root_path_spec))) #TODO DING DING DING
        print('')
        while len(scan_node.sub_nodes) == 1:
            scan_node = scan_node.sub_nodes[0]

        # The source scanner found a partition table and we need to determine
        # which partition needs to be processed.
        if scan_node.type_indicator != definitions.TYPE_INDICATOR_TSK_PARTITION:
            partition_identifiers = None
        else:
            partition_identifiers = self._get_tsk_partition_identifiers(scan_node, interactive)

        if self.initialized < 0:
            return

        base_path_specs = []
        if not partition_identifiers:
            self._scan_volume(scan_context, scan_node, base_path_specs, interactive)
        else:
            for partition_identifier in partition_identifiers:
                location = u'/{0:s}'.format(partition_identifier)
                sub_scan_node = scan_node.GetSubNodeByLocation(location)
                self._scan_volume(scan_context, sub_scan_node, base_path_specs, interactive)

        if self.initialized < 0:
            return
        else:
            self.initialized = 1

        if not base_path_specs:
            raise RuntimeError(
                u'No supported file system found in source.')

        return base_path_specs