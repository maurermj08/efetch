"""
Extracts 7z, ace, cab, gzip, iso, lzh, and rar using sflock
"""

from sflock.abstracts import File
from sflock.main import unpack
from yapsy.IPlugin import IPlugin
import logging
import os
import shutil


class Directory(IPlugin):

    def __init__(self):
        self.display_name = 'Extract'
        self.popularity = 7
        self.category = 'misc'
        self.cache = True
        self.fast = False
        self.action = False
        self.icon = 'fa-archive'

        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        extensions = [ '7z', 'bup', 'ace', 'cab', 'lzh', 'rar' ]
        return evidence['extension'] in extensions

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        # Prep extract directory
        extract_directory = os.path.join(evidence['file_cache_dir'], 'fa_extract')
        if os.path.exists(extract_directory):
            shutil.rmtree(extract_directory)
        os.mkdir(extract_directory)
        
        # Extract
        # TODO Change preserve from False to True
        unpacked = unpack(path_on_disk)
        unpacked.extract(extract_directory, preserve=False)
        return helper.plugin_manager.run_plugin_from_cache('directory', extract_directory, helper, request)
