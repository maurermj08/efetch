"""
Gets an overview of the file without using cache
"""

from yapsy.IPlugin import IPlugin
import os


class Overview(IPlugin):
    def __init__(self):
        self.display_name = 'Overview'
        self.popularity = 10
        self.cache = False
        self._order = [ 'thumbnail', 'path', 'mtime', 'atime', 'ctime', 'crtime', 'file_size', 'pid', 'mimetype', 'dir',
                        'name', 'ext', 'root', 'iid']
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
        if evidence['meta_type'] =='File' and not evidence['mimetype_known']:
            evidence['mimetype'] = helper.pathspec_helper.get_mimetype(evidence['pathspec'])
            evidence['mimetype_known'] = True

        listing = []

        for item in self._order:
            if item == 'thumbnail':
                listing.append('<tr><td>' + str(item) + '</td><td><img src="'
                               + helper.get_icon(evidence) + '" alt="' + evidence['meta_type'] + '-'
                               + evidence['extension'] + '" title="' + evidence['meta_type']
                        + '-' + evidence['extension'] + '" style="height:64px;"></td></tr>')
            elif item in evidence:
                listing.append('<tr><td>' + str(item) + '</td><td>' + str(evidence[item]) + '</td></tr>')

        for item in sorted(evidence):
            if item not in self._order:
                listing.append('<tr><td>' + str(item) + '</td><td>' + str(evidence[item]) + '</td></tr>')

        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/overview_template.html', 'r')
        html = str(template.read())
        template.close()

        html = html.replace('<!-- Table -->', '\n'.join(listing))

        return html
