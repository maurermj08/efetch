"""
A simple plugin that takes a file and returns the Strings in it
"""

from yapsy.IPlugin import IPlugin

class FaHexdump(IPlugin):

    
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
        return "Hex View"

    def check(self, mimetype, size):
        """Checks if the file is compatable with this plugin"""
        maxsize = 100000000 
        if (size < maxsize):
            return True
        else:
            return False

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, input_file, path_on_disk, mimetype, size):
        """Returns the result of this plugin to be displayed in a browser"""
        return "<xmp>" + self.hex_dump(input_file.read()) + "</xmp>"

    def hex_dump(self, src, length=16, sep='.'):
        FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or sep for x in range(256)])
        lines = []
        for c in xrange(0, len(src), length):
            chars = src[c:c+length]
            hex = ' '.join(["%02x" % ord(x) for x in chars])
            if len(hex) > 24:
                hex = "%s %s" % (hex[:24], hex[24:])
            printable = ''.join(["%s" % ((ord(x) <= 127 and FILTER[ord(x)]) or sep) for x in chars])
            lines.append("%08x:  %-*s  |%s|\n" % (c, length*3, hex, printable))
        return ''.join(lines)
