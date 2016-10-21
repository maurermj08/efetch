"""
Opens Exif lat long on google maps
"""

from yapsy.IPlugin import IPlugin
import PIL.Image
import PIL.ExifTags

class FaExifmap(IPlugin):

    def __init__(self):
        self.display_name = 'Exif Map'
        self.popularity = 0 # To enable change to 4
        self.cache = True
        self.fast = False
        self.action = False
        self.icon = 'fa-map-marker'
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

        exif_data = get_exif_data(image)
        lat_long = get_lat_lon(exif_data)

        key = ''

        if not lat_long:
            return '<xmp>No GPS data found</xmp>'

        if key:
            return '<body style="padding: 0px; margin: 0px;"><iframe src="https://google.com/maps/embed/v1/' + \
                   'place?key=' + key + '&q=loc:' + str(lat_long[0]) + \
                   ',' + str(lat_long[1]) + '" height="100%" width="100%"></iframe></body>'
        else:
            return '<a target="_blank" href="https://maps.google.com/' + \
                   '?q=loc:' + str(lat_long[0]) + \
                   ',' + str(lat_long[1]) + '">Link to Map (to embed a map a key must be provided)</a>'


def get_exif_data(image):
    """Returns a dictionary from the exif data of an PIL Image item. Also converts the GPS Tags"""
    exif_data = {}
    info = image._getexif()
    if info:
        for tag, value in info.items():
            decoded = PIL.ExifTags.TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                gps_data = {}
                for t in value:
                    sub_decoded = PIL.ExifTags.GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]

                exif_data[decoded] = gps_data
            else:
                exif_data[decoded] = value

    return exif_data


def _get_if_exist(data, key):
    if key in data:
        return data[key]

    return None


def _convert_to_degress(value):
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


def get_lat_lon(exif_data):
    """Returns the latitude and longitude, if available, from the provided exif_data (obtained through get_exif_data above)"""
    lat = None
    lon = None

    if "GPSInfo" in exif_data:
        gps_info = exif_data["GPSInfo"]

        gps_latitude = _get_if_exist(gps_info, "GPSLatitude")
        gps_latitude_ref = _get_if_exist(gps_info, 'GPSLatitudeRef')
        gps_longitude = _get_if_exist(gps_info, 'GPSLongitude')
        gps_longitude_ref = _get_if_exist(gps_info, 'GPSLongitudeRef')

        if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
            lat = _convert_to_degress(gps_latitude)
            if gps_latitude_ref != "N":
                lat = 0 - lat

            lon = _convert_to_degress(gps_longitude)
            if gps_longitude_ref != "E":
                lon = 0 - lon

    return lat, lon