"""
Simple directory tree view
"""

from yapsy.IPlugin import IPlugin
from flask import render_template, jsonify
from efetch_server.utils.pathspec_helper import PathspecHelper
import json
import logging
import os


LISTING_INTERVAL = 512

class Directory(IPlugin):

    def __init__(self):
        self.display_name = 'Navigate'
        self.popularity = 9
        self.category = 'misc'
        self.cache = False
        self.fast = False
        self.action = False
        self.icon = 'fa-folder-o'
        self._file_plugin = 'analyze'
        self._dir_plugin = 'directory'
        self._evidence_plugin = 'directory'

        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"


    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        directory_index = helper.get_request_value(request, 'directory_index', None)
        up = str(helper.get_request_value(request, 'up', False)) == 'True'
        location = helper.get_request_value(request, 'location', False)
        bad_location = False

        # Change location if modified
        if location == '':
            location = '/'
        if location:
            new_pathspec = PathspecHelper.set_pathspec_location(evidence['pathspec'], location)
            if new_pathspec:
                evidence['pathspec'] = new_pathspec
            else:
                bad_location = True

        # Initial call, just return the Template; else AJAX
        if directory_index is None:
            path_list = [ (True, evidence['pathspec'], PathspecHelper.get_file_path(evidence['pathspec'])) ]

            # Create filepath listing at top
            parent = PathspecHelper.get_parent_pathspec(evidence['pathspec'], True)
            while parent:
                file_name = PathspecHelper.get_file_name(parent)
                if file_name.lower() != 'none':
                    path_list.append((False, parent, PathspecHelper.get_file_name(parent)))
                parent = PathspecHelper.get_parent_pathspec(parent, True)  

            path_list.reverse()
            
            # Up arrow parent
            parent = PathspecHelper.get_parent_pathspec(evidence['pathspec'])
            # Prevents expandable evidence from being treated as a simple file
            if helper.is_expandable_evidence(evidence):
                pathspecs = helper.pathspec_helper.list_base_pathspecs(evidence)
                if len(pathspecs) > 0:
                    parent = PathspecHelper.get_parent_pathspec(pathspecs[0]['pathspec'])
            if evidence['meta_type'] != 'Directory':
                parent = PathspecHelper.get_parent_pathspec(parent)

            return render_template('directory.html', pathspec=evidence['pathspec'], 
                    path_list=path_list, parent=parent,up=up, bad_location=bad_location)
        else:
            directory_index = int(directory_index)

        directory_list = []

        # ORDER:
        #   1 - Up
        #   2 - Folders
        #   3 - Evidence and files

        # Forces volumes and partitions to be seen as expandable evidence
        force_expand = False

        # Moves the directory view up to the next expandable/directory pathspec
        #  and if the next one is '/' move up twice to the volume/partition root
        if not helper.is_expandable_evidence(evidence) and evidence['meta_type'] != 'Directory':
            evidence_parent = helper.pathspec_helper.get_parent_pathspec(evidence['pathspec'])
            evidence = helper.pathspec_helper.get_evidence_item(evidence_parent)
            return self.get(evidence, helper, path_on_disk, request)

        # Compressed files, only have 1 item
        if 'compression_type' in evidence:
            item_pathspec = helper.pathspec_helper.list_base_pathspecs(evidence)[0]['pathspec']
            items = [helper.pathspec_helper.get_evidence_item(item_pathspec)]
            initial_pathspec = evidence['pathspec']
        # Evidence
        elif helper.is_expandable_evidence(evidence):
            items = helper.pathspec_helper.list_base_pathspecs(evidence)

            # If moving up and only one item is there, go up (Prevents loop from next option)
            if len(items) == 1 and up:
                evidence_parent = helper.pathspec_helper.get_parent_pathspec(evidence['pathspec'])
                try:
                    evidence = helper.pathspec_helper.get_evidence_item(evidence_parent)
                except RuntimeError:
                    # Manually move up to the parent if getting the evidence item fails
                    logging.warn('Failed to get parent pathspec evidence item, manually moving up another pathspec')
                    evidence_parent = json.loads(evidence_parent)['parent']
                    evidence = helper.pathspec_helper.get_evidence_item(json.dumps(evidence_parent))
                return self.get(evidence, helper, path_on_disk, request)
            # If only one item (volume/partition/etc) go ahead and expand it
            elif len(items) == 1:
                items = helper.pathspec_helper.list_directory(items[0]['pathspec'],
                                                              offset=directory_index, size=LISTING_INTERVAL)
            else:
                force_expand = True

            initial_pathspec = evidence['pathspec']
        # Directories
        else:
            initial_pathspec = evidence['pathspec']

            while initial_pathspec and not getattr(helper.pathspec_helper._decode_pathspec(initial_pathspec), 'location', False):
                initial_pathspec = helper.pathspec_helper.get_encoded_parent_base_pathspec_manually(initial_pathspec)

            items = helper.pathspec_helper.list_directory(initial_pathspec, offset=directory_index,
                                                          size=LISTING_INTERVAL)

        # Gets the List of sub items to display
        for item in items:
            # Compressed files do not have file_names, and get the parent name minus the last extension
            if 'compression_type' in evidence:
                if 'file_name' not in item or not item['file_name']:
                    item['file_name'] = os.path.splitext(evidence['file_name'])[0]
            # If the file does not have a file name set it to '-' for the link
            if 'file_name' not in item or not item['file_name']:
                item['file_name'] = '-'

            # Remove nanoseconds for readability, values will be available on the overview page
            for time in ['mtime', 'atime', 'ctime', 'crtime']:
                if time in item:
                    item[time + '_no_nano'] = item[time].split('.')[0].replace('T', ' ')
                else:
                    item[time + '_no_nano'] = ''

            # Make human readable size
            if 'size' in item:
                item['size'] = Directory.human_readable_size(int(item['size']))

            # Get the icon here to limit the number of calls
            if not force_expand:
                item['icon'] = helper.get_icon(item)
            else:
                item['icon'] = '/static/icons/_evidence.png'

            # Always render analyze link
            item['analyze'] = True

            # Expandable evidence
            if helper.is_expandable_evidence(item) or force_expand:
                item['order'] = 3
                item['plugin'] = self._evidence_plugin
                item['download'] = True
                item['preview'] = True
            # Directories
            elif item['meta_type'] == 'Directory':
                item['order'] = 2
                item['plugin'] = self._dir_plugin
            # Files/Other
            else:
                item['order'] = 3
                item['target'] = 'target="_top"'
                item['plugin'] = self._file_plugin
                item['download'] = True
                item['preview'] = True

            if not 'size' in item:
                item['size'] = ''

            directory_list.append(item)

        # Gets the up directory option ".." if it is the first listing
        #if directory_index == 0:
            #parent_pathspec = helper.pathspec_helper.get_parent_pathspec(initial_pathspec)
            #if parent_pathspec:
            #    try:
            #        parent_item = helper.pathspec_helper.get_evidence_item(parent_pathspec)
            #    # Manually move up to the parent if getting the evidence item fails
            #    except RuntimeError:
            #        logging.warn('Failed to get parent pathspec evidence item, manually moving up another pathspec')
            #        parent_pathspec = json.loads(parent_pathspec)['parent']
            #        parent_item = helper.pathspec_helper.get_evidence_item(json.dumps(parent_pathspec))
            #if parent_pathspec and parent_item:
            #    parent_item['file_name'] = '..'
            #    parent_item['icon'] = '/static/icons/_folder_up.png'
            #    parent_item['order'] = 1
            #    parent_item['plugin'] = self._dir_plugin
            #    parent_item['url_query'] = parent_item['url_query'] + '&up=True'
            #    for time in ['mtime', 'atime', 'ctime', 'crtime']:
            #        parent_item[time + '_no_nano'] = ''
            #    # Make human readable size
            #    if 'size' in parent_item:
            #        parent_item['size'] = Directory.human_readable_size(int(parent_item['size']))
            #    directory_list.append(parent_item)

        # If there is nothing left to list, set directory_done to True
        directory_done = len(directory_list) == 0
        directory_index = directory_index + LISTING_INTERVAL

        # TODO directory_done will tell it to stop trying to load when it goes to the bottom
        return jsonify({'rows': directory_list, 'directory_index': directory_index, 'directory_done': directory_done})

    @staticmethod
    def human_readable_size(num, suffix='B'):
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 1000.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1000.0
        return "%.1f%s%s" % (num, 'Yi', suffix)
