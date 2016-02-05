"""
Converts a multimedia file to a HTML5 compatable file and displays it
"""

from yapsy.IPlugin import IPlugin
from bottle import static_file
import os

class FaMedia(IPlugin):

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
        return "Multimedia"

    def check(self, curr_file, path_on_disk, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        allowed = [ 'video/x-ms-asf','video/x-ms-asf','video/x-ms-asf-plugin','video/x-ms-asf','video/avi','video/msvideo','video/x-msvideo','video/avs-video','video/x-dv','video/dl','video/x-dl','video/x-dv','video/fli','video/x-fli','video/x-atomic3d-feature','video/gl','video/x-gl','video/x-isvideo','video/mpeg','video/mpeg','video/x-motion-jpeg','video/quicktime','video/quicktime','video/x-sgi-movie','video/mpeg','video/x-mpeg','video/x-mpeq2a','video/mpeg','video/x-mpeg','video/mpeg','video/mpeg','video/x-sgi-movie','video/x-qtc','video/x-scm','video/vnd.rn-realvideo','video/vdo','video/vivo','video/vnd.vivo','video/vosaic','video/x-amt-demorun','video/x-amt-showrun','audio/x-ms-wmv' ]
        return curr_file['meta_type'] == 'File' and str(mimetype).lower() in allowed

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 7

    def parent(self):
        """Returns if the plugin accepts other plugins (True) or only files (False)"""
        return False

    def cache(self):
        """Returns if caching is required"""
        return True

    def get(self, curr_file, helper, path_on_disk, mimetype, size, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        newname = os.path.splitext(path_on_disk)[0] + ".mp4"
        if not os.path.isfile(newname):
            os.system("avconv -i " + path_on_disk + " -c:v libx264 -c:a copy -acodec aac -strict experimental " + newname)
        return static_file(os.path.basename(newname), root=os.path.dirname(newname))

