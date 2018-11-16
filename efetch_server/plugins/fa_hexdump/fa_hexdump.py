"""
Returns a static HTML page with the hexdump output, similar to Hexdump -C
"""

from flask import render_template, jsonify
from yapsy.IPlugin import IPlugin


BUFFER_SIZE = 1024 * 8

class FaHexdump(IPlugin):
    def __init__(self):
        self.display_name = 'Hex View'
        self.popularity = 3
        self.category = 'common'
        self.cache = False
        self.fast = False
        self.action = False
        self.icon = 'fa-file-code-o'
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
        buffer = helper.get_request_value(request, 'buffer', None)

        if buffer is None:
            return render_template('fa_hexdump.html', pathspec=evidence['pathspec'])

        buffer = int(buffer)
        hex_data = self.hex_dump(helper.pathspec_helper.read_file(evidence['pathspec'],
                                                                  size=BUFFER_SIZE, seek=buffer * BUFFER_SIZE))
        hex_data['buffer'] = buffer + 1

        return jsonify(hex_data)

    def hex_dump(self, src, length=16, sep='.'):
        FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or sep for x in range(256)])
        offsets = []
        hexadecimals = []
        printables = []

        for c in xrange(0, len(src), length):
            chars = src[c:c + length]
            hex = ' '.join(["%02x" % ord(x) for x in chars])
            if len(hex) > 24:
                hex = "%s %s" % (hex[:24], hex[24:])
            printable = ''.join(["%s" % ((ord(x) <= 127 and FILTER[ord(x)]) or sep) for x in chars])
            offsets.append('%08x' % c)
            hexadecimals.append('%-*s' % (length * 3, hex))
            printables.append(printable)

        return {
            'offsets': offsets,
            'hexadecimals': hexadecimals,
            'printables': printables
        }
