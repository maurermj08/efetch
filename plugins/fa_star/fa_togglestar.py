"""
Toggles the bookmark of a single evidence item
"""

from yapsy.IPlugin import IPlugin
from bottle import abort
import logging
import json

class FaTogglestar(IPlugin):

    def __init__(self):
        self.display_name = 'Toggle Bookmark'
        self.popularity = 0
        self.parent = False
        self.cache = False
        self.fast = True
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
        index = helper.get_request_value(request, 'index', False)
        if not index:
            abort(400, 'Index required to Star Elasticsearch doc')

        id_value = helper.get_request_value(request, 'id', False)
        if not id_value and '_id' not in evidence:
            abort(400, 'ID required to Star Elasticsearch doc')
        elif not id_value:
            id_value = evidence['_id']

        starred = False
        data = {'img_id':id_value}

        event = helper.db_util.query_uuid(id_value, index)
        if '_index' in event:
            index = event['_index']

        if not event:
            logging.warn('Toggle Start failed to find event with ID "' + id_value + '"')
            abort(400, 'Failed to find event wit ID "' + id_value + '"')
        doc_type = event['_type']
        source = event['_source']

        try:
            starred = 'star' not in source or not source['star']
        except:
            logging.warn('Failed to star event, id "' + id_value + '" not found')
            abort(404, 'Could not find event')

        if starred:
            helper.db_util.update(id_value, index, {'star': True}, doc_type=doc_type)
            data['img'] = '/resources/images/bookmarked.png'
        else:
            helper.db_util.update(id_value, index, {'star': False}, doc_type=doc_type)
            data['img'] = '/resources/images/notbookmarked.png'

        return json.dumps(data)
