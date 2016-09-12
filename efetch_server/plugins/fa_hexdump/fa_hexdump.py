"""
Returns a static HTML page with the hexdump output, similar to Hexdump -C
"""

from yapsy.IPlugin import IPlugin


class FaHexdump(IPlugin):
    def __init__(self):
        self.display_name = 'Hex View'
        self.popularity = 5
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
        return evidence['meta_type'] == 'File'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        input_file = open(path_on_disk, 'rb')
        return "<xmp>" + self.hex_dump(input_file.read()) + "</xmp>"

    def hex_dump(self, src, length=16, sep='.'):
        FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or sep for x in range(256)])
        lines = []
        for c in xrange(0, len(src), length):
            chars = src[c:c + length]
            hex = ' '.join(["%02x" % ord(x) for x in chars])
            if len(hex) > 24:
                hex = "%s %s" % (hex[:24], hex[24:])
            printable = ''.join(["%s" % ((ord(x) <= 127 and FILTER[ord(x)]) or sep) for x in chars])
            lines.append("%08x:  %-*s  |%s|\n" % (c, length * 3, hex, printable))
        return ''.join(lines)
