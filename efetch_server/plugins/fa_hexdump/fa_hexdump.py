"""
Returns a static HTML page with the hexdump output, similar to Hexdump -C
"""

from flask import render_template_string, jsonify
from yapsy.IPlugin import IPlugin


BUFFER_SIZE = 1024 * 8

TEMPLATE = """
<!DOCTYPE html>
<html>
    <head>
        <script src="/static/jquery-1.11.3.min.js"></script>
        <script>
            var buffer = 0

            function get_hex() {
                $.ajax({
                      url: "/plugins/fa_hexdump?pathspec={{ pathspec | urlencode }}&buffer=" + buffer,
                      success: function (data) {
                          hex_object = JSON.parse(data)
                          for (var i in hex_object.hexadecimals){
                            $('table').append('<tr>' +
                                '<td><xmp>' + hex_object.offsets[i] + '</xmp></td>' +
                                '<td><xmp>' + hex_object.hexadecimals[i] + '</xmp></td>' +
                                '<td><xmp>' + hex_object.printables[i] + '</xmp></td>' +
                                '<td></td>' +
                                '</tr>');
                          }
                          buffer = hex_object.buffer;
                      },
                      dataType: 'html'
                });
            }

            $(window).scroll(function(){
                if ($(window).scrollTop() == $(document).height()-$(window).height()){
                    get_hex();
                }
            });

            window.onload = get_hex();
        </script>
        <style>
            body {
                margin: 0px;
            }

            table {
                width: 100%;
            }

            td, th {
                text-align: left;
                padding-left: 8px;
                padding-right: 8px;
            }

            td:last-child{
                width:100%;
                white-space:nowrap;
                background-color: white;
            }

            tr:nth-child(even) {
                background-color: #f1f1f1;
            }

            xmp {
                margin: 0px;
            }
        </style>
    </head>
    <body>
        <table>
        </table>
    </body>
</html>
"""
class FaHexdump(IPlugin):
    def __init__(self):
        self.display_name = 'Hex View'
        self.popularity = 3
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
            return render_template_string(TEMPLATE, pathspec=evidence['pathspec'])

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
