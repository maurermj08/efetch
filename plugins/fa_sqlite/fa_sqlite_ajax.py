"""
AJAX for SQLite Viewer plugin
"""

from yapsy.IPlugin import IPlugin
from bottle import route, run, static_file, response, post, abort
import json
import logging
import sqlite3
import sys

class FaSqliteAjax(IPlugin):
    def __init__(self):
        self.display_name = 'SQLite Ajax'
        self.popularity = 0
        self.cache = True
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
        return "application/json"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        method = request.query['method']

        if not method:
            abort(400, 'No method specified')
        elif method == "base":
            return self.base_tree(path_on_disk)
        elif method == "children":
            return self.get_children(request, path_on_disk)
        elif method == "values":
            return self.values(request, path_on_disk)

        return abort(400, 'Unknown method')

    def base_tree(self, path_on_disk):
        connection = sqlite3.connect(path_on_disk)
        cursor = connection.cursor()
        base_tree = []

        try:
            cursor.execute("SELECT * FROM sqlite_master WHERE type='table';")
            cursor.fetchone()
        except:
            abort(500, 'File does not have a SQLite Master table. The file might be corrupt or not a SQLite file.')

        # Master Table
        base_tree.append({'title': u'Master Table (1)',
                          'key': u'master',
                          'folder': True,
                          'lazy': True
                          })

        # Tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        base_tree.append({'title': u'Tables (' + unicode(len(tables)) + u')',
                          'key': u'table',
                          'folder': True,
                          'lazy': True
                          })

        # Views
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view';")
        views = cursor.fetchall()
        base_tree.append({'title': u'Views (' + unicode(len(views)) + u')',
                          'key': u'view',
                          'folder': True,
                          'lazy': True
                          })

        # Indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = cursor.fetchall()
        base_tree.append({'title': u'Indexes (' + unicode(len(indexes)) + u')',
                          'key': u'index',
                          'folder': True,
                          'lazy': True
                          })

        # Triggers
        cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger';")
        triggers = cursor.fetchall()
        base_tree.append({'title': u'Triggers (' + unicode(len(triggers)) + u')',
                          'key': u'trigger',
                          'folder': True,
                          'lazy': True
                          })
        response.content_type = 'application/json'

        connection.close()
        return json.dumps(base_tree)

    def get_children(self, request, path_on_disk):
        key = unicode(request.query['key'])
        children = []

        if key == u'master':
            children.append({'title': u'Master Table (1)',
                              'key': u'sqlite_master',
                             'folder': False,
                             'lazy': False
                           })
        else:
            for child in self.get_tables(key, path_on_disk):
                children.append({'title': child,
                                  'key': child,
                                 'folder': False,
                                 'lazy': False
                               })

        response.content_type = 'application/json'
        return json.dumps(children)

    def get_tables(self, key, path_on_disk):
        connection = sqlite3.connect(path_on_disk)
        cursor = connection.cursor()
        tables = []

        try:
            table_list = cursor.execute("SELECT name FROM sqlite_master WHERE type='" + key + "';")
        except:
            abort(500, 'Failed to parse type %s from the sqlite_master table.', key)

        for table in table_list:
            tables.append(unicode(table[0]))

        connection.close()
        return tables

    def values(self, request, path_on_disk):
        key = unicode(request.query['key'])

        connection = sqlite3.connect(path_on_disk)
        cursor = connection.cursor()
        response.content_type = 'application/json'

        try:
            cursor.execute("pragma table_info('" + key + "')")
        except:
            abort(500, 'Could not find table %s', key)

        rows = cursor.fetchall()

        table = [ u'<table id="sqlitet01" class="display">', u'    <thead><tr>' ]

        for row in rows:
            table.append(u'        <th>' + unicode(row[1]) + u'</th>')
        table.append(u'    </tr> </thead>')

        cursor.execute('SELECT * FROM ' + key)
        rows = cursor.fetchall()

        for row in rows:
            table.append(u'    <tr>')
            for item in row:
                try:
                    table.append(u'        <td>' + unicode(item) + u'</td>')
                except:
                     table.append(u'        <td>' + unicode(type(item)) + u'</td>')
            table.append(u'    </tr>')

        table.append(u'</table>')

        connection.close()
        return {'table': '\n'.join(table)}