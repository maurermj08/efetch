"""
Get EXIF Metadata
"""

from yapsy.IPlugin import IPlugin
import exifread

class FaExif(IPlugin):

    def __init__(self):
        self._display_name = 'Exif Info'
        self._popularity = 5
        self._parent = False
        self._cache = True
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        allowed = [ 'image/jpeg','image/tiff','image/x-tiff' ]
        return str(evidence['mimetype']).lower() in allowed

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children):
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
