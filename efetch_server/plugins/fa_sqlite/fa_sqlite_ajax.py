"""
AJAX for SQLite Viewer plugin
"""

from yapsy.IPlugin import IPlugin
from flask import Response, jsonify
import json
import logging
import sqlite3


class FaSqliteAjax(IPlugin):
    def __init__(self):
        self.display_name = 'SQLite Ajax'
        self.popularity = 0
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
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "application/json"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        method = helper.get_request_value(request, 'method', raise_key_error=True)

        if method == "base":
            return self.base_tree(path_on_disk)
        elif method == "children":
            return self.get_children(request, helper, path_on_disk)
        elif method == "values":
            return self.values(request, helper, path_on_disk)

        logging.error('Unknown method "' + method + '" provided')
        raise ValueError('Method "' + method + '" is not valid')

    def base_tree(self, path_on_disk):
        connection = sqlite3.connect(path_on_disk)
        cursor = connection.cursor()
        base_tree = []

        cursor.execute("SELECT * FROM sqlite_master WHERE type='table';")
        cursor.fetchone()

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

        connection.close()
        # TODO REPLACE WITH DICTIONARY AND JSONIFY, SEE: http://stackoverflow.com/questions/12435297/how-do-i-jsonify-a-list-in-flask
        return Response(json.dumps(base_tree), mimetype='application/json')

    def get_children(self, request, helper, path_on_disk):
        key = unicode(helper.get_request_value(request, 'key'))
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

        # TODO REPLACE WITH DICTIONARY AND JSONIFY, SEE: http://stackoverflow.com/questions/12435297/how-do-i-jsonify-a-list-in-flask
        return Response(json.dumps(children), mimetype='application/json')

    def get_tables(self, key, path_on_disk):
        connection = sqlite3.connect(path_on_disk)
        cursor = connection.cursor()
        tables = []
        table_list = cursor.execute("SELECT name FROM sqlite_master WHERE type='" + key + "';")

        for table in table_list:
            tables.append(unicode(table[0]))

        connection.close()
        return tables

    def values(self, request, helper, path_on_disk):
        key = unicode(helper.get_request_value(request, 'key'))

        connection = sqlite3.connect(path_on_disk)
        cursor = connection.cursor()
        cursor.execute("pragma table_info('" + key + "')")

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
        return jsonify({'table': '\n'.join(table)})