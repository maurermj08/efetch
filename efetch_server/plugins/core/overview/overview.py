"""
Gets an overview of the file without using cache
"""

from collections import OrderedDict
from flask import render_template
from yapsy.IPlugin import IPlugin


class Overview(IPlugin):
    def __init__(self):
        self.display_name = 'Overview'
        self.popularity = 10
        self.cache = False
        self._key_order = ['thumbnail', 'path', 'mtime', 'atime', 'ctime', 'crtime', 'file_size', 'pid', 'mimetype',
                           'dir', 'name', 'ext', 'root', 'iid']
        self.fast = False
        self.action = False
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

        # Get the file mimetype if it is currently unknown
        if evidence['meta_type'] =='File' and not evidence['mimetype_known']:
            evidence['mimetype'] = helper.pathspec_helper.get_mimetype(evidence['pathspec'])
            evidence['mimetype_known'] = True

        # Thumbnail
        evidence['thumbnail'] = '<img src="' + helper.get_icon(evidence) + '" alt="' + evidence['meta_type'] + '-'+ \
                                evidence['extension'] + '" title="' + evidence['meta_type']+ '-' + \
                                evidence['extension'] + '" style="height:64px;">'

        # Add missing keys to key_order
        for key in evidence:
            if not key in self._key_order:
                self._key_order.append(key)

        # Order the evidence
        ordered_evidence = OrderedDict(sorted(evidence.items(), key=lambda i:self._key_order.index(i[0])))

        return render_template('overview.html', evidence=ordered_evidence.items())
