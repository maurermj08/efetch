"""
This plugin returns common files that can be opened in a browser i.e. images and PDF documents
"""

from yapsy.IPlugin import IPlugin
from bottle import static_file
import os


class Preview(IPlugin):
    def __init__(self):
        self.display_name = 'Preview'
        self.popularity = 8
        self.cache = True
        self.fast = False
        self.action = False
        self.icon = 'fa-eye'
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        allowed_mimetype = ['application/xml', 'application/pdf', 'message/rfc822']
        allowed_prefix = ['image', 'text', 'video', 'audio']
        return (str(evidence['mimetype'].split('/')[0]).lower() in allowed_prefix
                or evidence['mimetype'] in allowed_mimetype ) and evidence['meta_type'] != 'Directory'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return mimetype

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        smart_redirect = helper.get_request_value(request, 'redirect', 'False').lower() in ['true', 't', 'y', 'yes']
        if smart_redirect and not self.check(evidence, path_on_disk):
            return helper.plugin_manager.get_plugin_by_name('analyze').get(evidence, helper, path_on_disk, request)

        return static_file(os.path.basename(path_on_disk), root=os.path.dirname(path_on_disk))
