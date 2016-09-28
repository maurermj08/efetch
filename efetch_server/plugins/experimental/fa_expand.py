"""
Navigates a new base evidence item, i.e. raw, E01, or zip file
"""

from yapsy.IPlugin import IPlugin
from yapsy.IPlugin import IPlugin
from jinja2 import Template


class FaExpand(IPlugin):

    def __init__(self):
        self.display_name = 'Expand'
        self.popularity = 8
        self.cache = False
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
        allowed_extensions = ['e01','raw','001','dd','vmdk']
        return evidence['extension'].lower() in allowed_extensions


    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    # TODO Clean and merge with navigate
    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        dir_table = []
        file_table = []
        row_evidence_tempalte = Template("""
            <tr>
                <td><img src="/resources/icons/evidence.png" style="width:32px;height:32px;"></td>
                <td><a href="/plugins/fa_directory?{{ url_query }}">{{file_name}}</a></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
        """)
        row_file_template = Template("""
            <tr>
                <!-- {{ file_name }} -->
                <td><img src="/plugins/thumbnail?{{ url_query }}" style="width:32px;height:32px;"></td>
                <td><a href="/plugins/analyze?{{ url_query }}" target="_top">{{file_name}}</a></td>
                <td>{{ mtime }}</td>
                <td>{{ atime }}</td>
                <td>{{ ctime }}</td>
                <td>{{ crtime }}</td>
                <td>{{ size }}</td>
            </tr>
        """)
        row_dir_template = Template("""
            <tr>
                <!-- {{ file_name }} -->
                <td><img src="/plugins/thumbnail?{{ url_query }}" style="width:32px;height:32px;"></td>
                <td><a href="/plugins/fa_directory?{{ url_query }}">{{file_name}}</a></td>
                <td>{{ mtime }}</td>
                <td>{{ atime }}</td>
                <td>{{ ctime }}</td>
                <td>{{ crtime }}</td>
                <td>{{ size }}</td>
            </tr>
        """)

        initial_pathspec = helper.pathspec_helper.get_new_base_pathspecs(evidence['pathspec'])

        if len(initial_pathspec) > 1:
            for item in initial_pathspec:
                dir_table.append(row_evidence_tempalte.render(item))
        else:
            for item in helper.pathspec_helper.list_directory(initial_pathspec[0]['pathspec']):
                if item['meta_type'] == 'Directory':
                    dir_table.append(row_dir_template.render(item))
                else:
                    file_table.append(row_file_template.render(item))

        dir_table.sort()
        file_table.sort()

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
                            <thead>
                            <tr>
                                <th>Icon</th>
                                <th>File Name</th>
                                <th>Modified</th>
                                <th>Accessed</th>
                                <th>Changed</th>
                                <th>Created</th>
                                <th>Size</th>
                            </tr>
                            </thead>
                            <tbody>'''\
                            + '\n'.join(dir_table) + '\n'.join(file_table) + '</tbody><table>' + \
               '''  </body>
               </html>'''
