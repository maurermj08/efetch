"""
Simple file browser
"""

from yapsy.IPlugin import IPlugin
import os
import time

class FaFileDirectory(IPlugin):

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
        return "File Directory"

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
        return True

    def cache(self):
        """Returns if caching is required"""
        return False

    def get(self, curr_file, helper, path_on_disk, mimetype, size, address, port, request, children):
        """Returns a formatted directory listing for the given path"""
        #If path is a folder just set the view to it, if not use the files parent folder
        if curr_file['file_type'] == 'directory':
            curr_folder = curr_file['path'] + "/"
        else:
            curr_folder = curr_file['dir']

        listing = []

        if curr_file['image_id'] in children:
            child_plugins = str(children).split(curr_file['image_id'])[0]
        if not child_plugins:
            child_plugins = 'fa_file_analyze/'
        
        if request.query_string:
            query_string = "?" + request.query_string
        else:
            query_string = ""
        
        #TODO: Change localtime to case time, specifically what is supplied to sleuthkit
        for item in helper.db_util.list_dir(helper.db_util.get_file(curr_file['image_id'], curr_file['offset'], curr_folder)):
            source = item['_source']
            if source['file_type'] != 'directory':
                listing.append("    <tr>") 
                listing.append('        <td><img src="http://' + address + ':' + port + '/plugins/fa_thumbnail/' + source['image_id'] + '/' + source['offset'] + source['path'] + '" alt="-" style="width:32px;height:32px;"></td>')
                if source['file_type'] == 'directory':
                    listing.append('        <td><a href="http://' + address + ':' + port + '/plugins/' + child_plugins + source['image_id'] + '/' + source['offset'] + source['path'] + query_string + '" target="file_dir_frame">' + source['name'] + "</a></td>")
                else:
                    listing.append('        <td><a href="http://' + address + ':' + port + '/plugins/' + child_plugins + source['image_id'] + '/' + source['offset'] + source['path'] + query_string + '" target="file_dir_frame">' + source['name'] + "</a></td>")
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
        template = open(curr_dir + '/file_dir_template.html', 'r')
        html = str(template.read())
        template.close()
       
        html = html.replace('<!-- Table -->', '\n'.join(listing))

        if str(children).startswith(curr_file['image_id']):
            html = html.replace('<!-- Home -->', "http://" + address + ":" + port + "/plugins/" + child_plugins + children + query_string)
        else:
            html = html.replace('<!-- Home -->', "http://" + address + ":" + port + "/plugins/" + children + query_string)


        return html

