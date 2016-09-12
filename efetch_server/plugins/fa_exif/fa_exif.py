"""
Prints ExifTags from an image using PIL
"""

from yapsy.IPlugin import IPlugin
import os
import PIL.Image
import PIL.ExifTags


class FaExif(IPlugin):

    def __init__(self):
        self.display_name = 'EXIF'
        self.popularity = 6
        self.cache = True
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
        allowed = [ 'image/jpeg', 'image/tiff', 'image/x-tiff' ]
        return evidence['mimetype'].lower() in allowed

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        image = PIL.Image.open(path_on_disk)
        if not image._getexif():
            return '<xmp>No Exif data found</xmp>'
        exif_data = {
            PIL.ExifTags.TAGS[k]: v
            for k, v in image._getexif().items()
            if k in PIL.ExifTags.TAGS
        }

        table = []

        for key, value in exif_data.iteritems():
            table.append('<tr><td>' + str(key) + '</td><td>' + str(value)  + '</td></tr>')

        return '''
        <!DOCTYPE html>
        <html>
        <head>
                <script src="/resources/jquery-1.11.3.min.js"></script>
                <script src="/resources/jquery-ui-1.11.4/jquery-ui.min.js" type="text/javascript"></script>
                <link rel="stylesheet" type="text/css" href="/resources/themes/icon.css">
                <link rel="stylesheet" type="text/css" href="/resources/themes/jquery.dataTables.min.css">
                <script type="text/javascript" src="/resources/jquery.dataTables.min.js"></script>
                <script type="text/javascript" class="init">
                    $(document).ready(function() {
                            $('#t01').DataTable({
                                    "paging": false,
                                    "info": false,
                                    "searching": false,
                                    "ordering": false,
                                    "orderClasses": false
                                    }
                            );
                    } );
                </script>
        <style>
            table {
                overflow-y: scroll;
                width: 100%;
            }
            table, th, td {
                border: 0px;
                border-collapse: collapse;
            }
            th, td {
                padding: 5px;
                text-align: left;
            }
            table#t01 tr:nth-child(even) {
                background-color: #fff;
            }
            table#t01 tr:nth-child(odd) {
               background-color:#eee;
            }
            table#t01 th {
                background-color: #E9F1FF;
                color: #0E2D87;
            }
            html{
                height: 100%;
            }

            body {
                min-height: 100%;
                margin: 0px;
            }

        </style>
        </head>
            <body>
                <table id="t01" class="display">
                    ''' + '\n'.join(table) + '''
                </table>
        </body>
        </html>
        '''