"""
Gets an overview of the file without using cache
"""

from collections import OrderedDict
from flask import render_template_string
from yapsy.IPlugin import IPlugin


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
                    {% for key, value in evidence %}
                        <tr><td>{{ key }}</td><td>{{ value }}</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </body>
    </html>
"""

class Overview(IPlugin):
    def __init__(self):
        self.display_name = 'Overview'
        self.popularity = 10
        self.cache = False
        self._key_order = ['thumbnail', 'path', 'mtime', 'atime', 'ctime', 'crtime', 'file_size', 'pid', 'mimetype',
                           'dir', 'name', 'ext', 'root', 'iid']
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
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""

        # Get the file mimetype if it is currently unknown
        if evidence['meta_type'] =='File' and not evidence['mimetype_known']:
            evidence['mimetype'] = helper.pathspec_helper.get_mimetype(evidence['pathspec'])
            evidence['mimetype_known'] = True

        # Thumbnail
        evidence['thumbnail'] = '<img src="' + helper.get_icon(evidence) + '" alt="' + evidence['meta_type'] + '-'+ \
                                evidence['extension'] + '" title="' + evidence['meta_type']+ '-' + \
                                evidence['extension'] + '" style="height:64px;">'

        # Add missing keys to key_order
        for key in evidence:
            if not key in self._key_order:
                self._key_order.append(key)

        # Order the evidence
        ordered_evidence = OrderedDict(sorted(evidence.items(), key=lambda i:self._key_order.index(i[0])))

        return render_template_string(TEMPLATE, evidence=ordered_evidence.items())
