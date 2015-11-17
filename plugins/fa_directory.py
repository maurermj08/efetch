"""
Simple file browser
"""

from yapsy.IPlugin import IPlugin
import os

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
        return 5

    def cache(self):
        """Returns if caching is required"""
        return False

    def get(self, curr_file, helper, path_on_disk, mimetype, size, address, port, request_query):
        """Returns a formatted directory listing for the given path"""
        #If path is a folder just set the view to it, if not use the files parent folder
        if curr_file['file_type'] == 'directory':
            curr_folder = curr_file['path'] + "/"
        else:
            curr_folder = curr_file['dir']

        listing = []
        #TODO: Change localtime to case time, specifically what is supplied to sleuthkit
        for item in db_util.list_dir(db_util.get_file(curr_file['image_id'], curr_file['offset'], curr_folder)):
            listing.append("    <tr>") 
            listing.append('        <td><img src="http://' + address + ':' + port + '/plugin/fa_thumbnail/' + item['image_id'] + '/' + item['offset'] + item['path'] + '" alt="-" style="width:32px;height:32px;"></td>')
            if item['file_type'] == 'directory':
                listing.append('        <td><a href="http://' + address + ':' + port + '/plugin/fa_directory/' + item['image_id'] + '/' + item['offset'] + item['path'] + '" target="_self">' + item['name'] + "</a></td>")
            else:
                listing.append('        <td><a href="http://' + address + ':' + port + '/plugin/fa_analyze/' + item['image_id'] + '/' + item['offset'] + item['path'] + '" target="_top">' + item['name'] + "</a></td>")
            if (item['mod']):
                listing.append("        <td>" + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(item['mod']))) + "</td>")
            else:
                listing.append("        <td> - </td>")
            if (item['acc']):
                listing.append("        <td>" + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(item['acc']))) + "</td>")
            else:
                listing.append("        <td> - </td>")
            if (item['chg']):
                listing.append("        <td>" + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(item['chg']))) + "</td>")
            else:
                listing.append("        <td> - </td>")
            if (item['cre']):
                listing.append("        <td>" + time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(float(item['cre']))) + "</td>")
            else:
                listing.append("        <td> - </td>")
            listing.append("        <td>" + item['size'] + "</td>")
            listing.append("    </tr>")

        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/dir_template.html', 'r')
        html = str(template.read())
        html = html.replace('<!-- Table -->', '\n'.join(listing))

        return html

