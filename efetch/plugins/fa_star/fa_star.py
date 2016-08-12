"""
Bookmarks an evidence item
"""

from yapsy.IPlugin import IPlugin
import os


class FaStar(IPlugin):

    def __init__(self):
        self.display_name = 'Bookmark'
        self.popularity = 0
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

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        helper.db_util.update(evidence['pid'], evidence['image_id'], {'star': True})
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        return open(curr_dir + '/star_template.html', 'r')
