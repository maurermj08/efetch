"""
Simple file browser
"""

from yapsy.IPlugin import IPlugin
import os
import time

class FaDirectory(IPlugin):

    def __init__(self):
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def display_name(self):
        """Returns the name displayed in the webview"""
        return "Directory"

    def check(self, curr_file, path_on_disk, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 0

    def parent(self):
        """Returns if the plugin accepts other plugins (True) or only files (False)"""
        return False

    def cache(self):
        """Returns if caching is required"""
        return False

    def get(self, curr_file, helper, path_on_disk, mimetype, size, address, port, request, children):
        """Returns a formatted directory listing for the given path"""
        #If path is a folder just set the view to it, if not use the files parent folder
        if curr_file['file_type'] == 'directory':
            curr_folder = curr_file
        else:
            curr_folder = helper.db_util.get_file(curr_file['image_id'], curr_file['dir'])

        listing = []
        #TODO: Change localtime to case time, specifically what is supplied to sleuthkit
        for item in helper.db_util.list_dir(curr_folder):
            source = item['_source']
            listing.append("    <tr>") 
            listing.append('        <td><img src="/plugins/fa_thumbnail/' + source['pid'] + '" alt="' + source['file_type'] + '-' + source['ext'] + '" title="' + source['file_type'] + '-' + source['ext'] + '" style="width:32px;height:32px;"></td>')
            if source['file_type'] == 'directory':
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
            listing.append("        <td>" + source['size'] + "</td>")
            listing.append("    </tr>")

        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/dir_template.html', 'r')
        html = str(template.read())
        template.close()
        html = html.replace('<!-- Table -->', '\n'.join(listing))

        return html

