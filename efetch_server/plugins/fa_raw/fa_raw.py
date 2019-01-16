"""
Displays the printable characters of the file
"""

from yapsy.IPlugin import IPlugin
from efetch_server.utils.pathspec_helper import PathspecHelper
from flask import render_template
import unicodedata
import re


class FaRaw(IPlugin):

    def __init__(self):
        self.display_name = 'Raw View'
        self.popularity = 5
        self.category = 'common'
        self.cache = False
        self.fast = False
        self.action = False
        self.icon = 'fa-code'
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        return evidence['meta_type'] == 'File'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        data = PathspecHelper.read_file(evidence['pathspec'], size=evidence['size'], seek=0)	
        chars = ''.join(map(unichr, range(0,9) + range(11,32) + range(127,160)))
        regexp = re.compile('[%s]' % re.escape(chars))
        return render_template('fa_raw.html', data=regexp.sub('', data.decode('utf8', 'ignore')).split('\n', -1))
