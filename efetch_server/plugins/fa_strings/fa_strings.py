"""
A simple plugin that takes a file and returns the Strings in it
"""

from flask import render_template, jsonify
from yapsy.IPlugin import IPlugin


BUFFER_SIZE = 1024 * 1024
NUMBER_OF_STRINGS = 256
MINIMUM_CHARACTERS = 4

# TODO: Boundary strings... Any strings at a buffer Boundary will be broken up and some small strings will be ingored
class FaStrings(IPlugin):
    def __init__(self):
        self.display_name = 'Strings'
        self.popularity = 4
        self.category = 'common'
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
            return render_template('fa_strings.html', pathspec=evidence['pathspec'])

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
