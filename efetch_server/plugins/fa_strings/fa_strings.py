"""
A simple plugin that takes a file and returns the Strings in it
"""

from flask import render_template_string, jsonify
from yapsy.IPlugin import IPlugin


BUFFER_SIZE = 1024 * 1024
NUMBER_OF_STRINGS = 256
MINIMUM_CHARACTERS = 4

TEMPLATE = """
<!DOCTYPE html>
<html>
    <head>
        <script src="/static/jquery-1.11.3.min.js"></script>
        <script>
            var buffer = 0
            var index_in_buffer = 0

            function get_strings() {
                $.ajax({
                      url: "/plugins/fa_strings?pathspec={{ pathspec | urlencode }}&buffer=" + buffer + "&index_in_buffer=" + index_in_buffer,
                      success: function (data) {
                          string_object = JSON.parse(data)
                          for (var i in string_object.strings){
                            $('table').append('<tr><td><xmp>' + string_object.strings[i] + '</xmp></td></tr>');
                          }
                          buffer = string_object.buffer;
                          index_in_buffer = string_object.index_in_buffer;
                      },
                      dataType: 'html'
                });
            }

            $(window).scroll(function(){
                if ($(window).scrollTop() == $(document).height()-$(window).height()){
                    get_strings()
                }
            });

            window.onload = get_strings()
        </script>
        <style>
            body {
                margin: 0px;
            }

            table {
                font-family: arial, sans-serif;
                width: 100%;
            }

            td, th {
                text-align: left;
                padding-left: 8px;
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

# TODO: Boundary strings... Any strings at a buffer Boundary will be broken up and some small strings will be ingored
class FaStrings(IPlugin):
    def __init__(self):
        self.display_name = 'Strings'
        self.popularity = 4
        self.cache = False
        self.fast = False
        self.action = False
        self.icon = 'fa-file-text-o'
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
        # Index of the last string in the buffer
        index_in_buffer = helper.get_request_value(request, 'index_in_buffer', 0)
        list_of_strings = []

        if buffer is None:
            return render_template_string(TEMPLATE, pathspec=evidence['pathspec'])

        buffer = int(buffer)
        index_in_buffer = int(index_in_buffer)
        missing_strings = 0

        while len(list_of_strings) < NUMBER_OF_STRINGS and buffer * BUFFER_SIZE < evidence['size']:
            missing_strings = NUMBER_OF_STRINGS - len(list_of_strings)
            new_strings = helper.pathspec_helper.get_file_strings(evidence['pathspec'], MINIMUM_CHARACTERS,
                                                                  BUFFER_SIZE, buffer * BUFFER_SIZE)[index_in_buffer:]
            list_of_strings.extend(new_strings[:missing_strings])
            buffer += 1

        return jsonify({'strings': list_of_strings, 'buffer': buffer, 'index_in_buffer': missing_strings})