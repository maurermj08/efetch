"""
Simple file browser
"""

from yapsy.IPlugin import IPlugin
import os
import time

class FaDirectory(IPlugin):

    def __init__(self):
        self._display_name = 'Directory'
        self._popularity = 0
        self._parent = False
        self._cache = False
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns a formatted directory listing for the given path"""
        #If path is a folder just set the view to it, if not use the files parent folder
        if evidence['meta_type'] == 'Directory':
            curr_folder = evidence
        else:
            curr_folder = helper.db_util.get_file(evidence['image_id'], evidence['dir'])

        listing = []
        #TODO: Change localtime to case time, specifically what is supplied to sleuthkit
        for item in helper.db_util.bool_query_evidence(curr_folder):
            source = item['_source']
            listing.append("    <tr>") 
            listing.append('        <td><img src="/plugins/fa_thumbnail/' + source['pid'] + '" alt="' + source['meta_type'] + '-' + source['ext'] + '" title="' + source['meta_type'] + '-' + source['ext'] + '" style="width:32px;height:32px;"></td>')
            if source['meta_type'] == 'Directory':
                listing.append('        <td><a href="/plugins/fa_directory/' + source['pid'] + '" target="_self">' + source['name'] + "</a></td>")
            else:
                listing.append('        <td><a href="/plugins/fa_analyze/' + source['pid'] + '" target="_parent">' + source['name'] + "</a></td>")
            if (source['mod']):
                listing.append("        <td>" + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(source['mod']))) + "</td>")
            else:
                listing.append("        <td> - </td>")
            if (source['acc']):
                listing.append("        <td>" + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(source['acc']))) + "</td>")
            else:
                listing.append("        <td> - </td>")
            if (source['chg']):
                listing.append("        <td>" + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(source['chg']))) + "</td>")
            else:
                listing.append("        <td> - </td>")
            if (source['cre']):
                listing.append("        <td>" + time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(float(source['cre']))) + "</td>")
            else:
                listing.append("        <td> - </td>")
            if 'bookmark' not in source or source['bookmark'] == 'false':
                listing.append("        <td> NONE </td>")
            else:
                listing.append("        <td> BOOKMARKED </td>")
            listing.append("        <td>" + str(source['file_size']) + "</td>")
            listing.append("    </tr>")

        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/dir_template.html', 'r')
        html = str(template.read())
        template.close()
        html = html.replace('<!-- Table -->', '\n'.join(listing))

        return html

