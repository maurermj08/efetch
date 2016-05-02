"""
Toggles the bookmark of a single evidence item
"""

from yapsy.IPlugin import IPlugin
import logging
import json


class FaTogglestar(IPlugin):

    def __init__(self):
        self.display_name = 'Toggle Bookmark'
        self.popularity = 0
        self.parent = False
        self.cache = False
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

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        data = {}

        data['img_id'] = helper.get_request_value(request, 'image_id', False)

        if not data['img_id']:
            logging.warn('No "image_id" found for toggle star')

        if 'star' not in evidence or not evidence['star']:
            helper.db_util.update_by_ppid(evidence['pid'], {'star': True})
            data['img'] = '/resources/images/bookmarked.png'
        else:
            helper.db_util.update_by_ppid(evidence['pid'], {'star': False})
            data['img'] = '/resources/images/notbookmarked.png'

        return json.dumps(data)
