"""
Get EXIF Metadata
"""

from yapsy.IPlugin import IPlugin
import exifread

class FaExif(IPlugin):

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
        return "Exif Info"

    def check(self, curr_file, path_on_disk, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        allowed = [ 'image/jpeg','image/tiff','image/x-tiff' ]
        return str(mimetype).lower() in allowed

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 5

    def parent(self):
        """Returns if the plugin accepts other plugins (True) or only files (False)"""
        return False

    def cache(self):
        """Returns if caching is required"""
        return True

    def get(self, curr_file, helper, path_on_disk, mimetype, size, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        fh = open(path_on_disk,'rb') 
        exif_dict = exifread.process_file(fh)
        fh.close()
        tags = exif_dict.keys()
        data = '<xmp style="white-space: pre-wrap;">\n'
        if len(tags) > 0:
            for tag in tags:
                if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote'):	
                    data += str(tag) + ": " + str(exif_dict[tag]) + "\n"
            data += "\n"
        else:
            data += "No EXIF Data Found\n"
        data += '</xmp>'
        return data
