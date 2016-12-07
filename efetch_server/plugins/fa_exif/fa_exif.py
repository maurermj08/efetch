"""
Prints ExifTags from an image using PIL
"""

from yapsy.IPlugin import IPlugin
try:
    from PIL import Image, ExifTags
except ImportError:
    Image = None
import os
from flask import render_template_string


TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
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
            text-align: left;
            padding: 10px;
        }
        table#t01 tr:nth-child(even) {
            background-color: #fff;
        }
        table#t01 tr:nth-child(odd) {
           background-color:#eee;
        }
        table#t01 th {
            background-color: #444;
            color: white;
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
                <thead>
                <tr>
                    <th>Name</th>
                    <th>Value</th>
                </tr>
                </thead>
                <tbody>
                    {% for key, value in table %}
                        <tr><td>{{ key }}</td><td>{{ value }}</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </body>
    </html>
    """


class FaExif(IPlugin):

    def __init__(self):
        self.display_name = 'EXIF'
        self.popularity = 6
        self.cache = True
        self.fast = False
        self.action = False
        self.icon = 'fa-file-image-o'
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
        return evidence['mimetype'].lower() in allowed and Image

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        cached = os.path.isfile(evidence['file_cache_path'])
        if cached:
            image = Image.open(evidence['file_cache_path'])
        else:
            image = Image.open(self._open_file_object(evidence['pathspec']))
        if not image._getexif():
            return '<xmp>No Exif data found</xmp>'
        exif_data = {
            ExifTags.TAGS[k]: v
            for k, v in image._getexif().items()
            if k in ExifTags.TAGS
        }

        table = []

        for key, value in exif_data.iteritems():
            table.append((key, value))
            if key == 'GPSInfo':
                lat_long = get_lat_lon(value)
                table.append(('Google Maps', '<a target="_blank" href="https://maps.google.com/?q=loc:'
                              + str(lat_long[0]) + ',' + str(lat_long[1]) + '">Link to Google Maps</a>'))

        return render_template_string(TEMPLATE, table=table)


def get_exif_data(image):
    """Returns a dictionary from the exif data of an PIL Image item. Also converts the GPS Tags"""
    exif_data = {}
    info = image._getexif()
    if info:
        for tag, value in info.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                gps_data = {}
                for t in value:
                    sub_decoded = ExifTags.GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]

                exif_data[decoded] = gps_data
            else:
                exif_data[decoded] = value

    return exif_data


def _get_if_exist(data, key):
    if key in data:
        return data[key]

    return None


def _convert_to_degrees(value):
    """Helper function to convert the GPS coordinates stored in the EXIF to degress in float format"""
    d0 = value[0][0]
    d1 = value[0][1]
    d = float(d0) / float(d1)

    m0 = value[1][0]
    m1 = value[1][1]
    m = float(m0) / float(m1)

    s0 = value[2][0]
    s1 = value[2][1]
    s = float(s0) / float(s1)

    return d + (m / 60.0) + (s / 3600.0)


def get_lat_lon(gps_info_value):
    """Returns the latitude and longitude, if available, from the provided exif_data (obtained through get_exif_data above)"""
    lat = 0
    lon = 0

    gps_info = {}
    for t in gps_info_value:
        sub_decoded = ExifTags.GPSTAGS.get(t, t)
        gps_info[sub_decoded] = gps_info_value[t]

    gps_latitude = _get_if_exist(gps_info, "GPSLatitude")
    gps_latitude_ref = _get_if_exist(gps_info, 'GPSLatitudeRef')
    gps_longitude = _get_if_exist(gps_info, 'GPSLongitude')
    gps_longitude_ref = _get_if_exist(gps_info, 'GPSLongitudeRef')

    if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
        lat = _convert_to_degrees(gps_latitude)
        if gps_latitude_ref != "N":
            lat = 0 - lat

        lon = _convert_to_degrees(gps_longitude)
        if gps_longitude_ref != "E":
            lon = 0 - lon

    return lat, lon