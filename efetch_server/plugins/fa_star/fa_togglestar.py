"""
Toggles the bookmark of a single evidence item
"""

import logging
from flask import jsonify
from yapsy.IPlugin import IPlugin


class FaTogglestar(IPlugin):

    def __init__(self):
        self.display_name = 'Toggle Bookmark'
        self.popularity = 0
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
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        index = helper.get_request_value(request, 'index', False, raise_key_error=True)
        uuid_value = helper.get_request_value(request, 'id', False, raise_key_error=True)

        if not uuid_value:
            uuid_value = evidence['_id']

        data = {'img_id':uuid_value}
        event = helper.db_util.query_uuid(uuid_value, index)

        if '_index' in event:
            index = event['_index']
        if '_id' in event:
            id_value = event['_id']
        else:
            logging.warn('No _id found in event, using uuid')
            id_value = uuid_value

        if not event:
            logging.error('Toggle Start failed to find event with ID "' + uuid_value + '"')
            raise ValueError('Failed to find event wit ID "' + uuid_value + '"')

        doc_type = event['_type']
        source = event['_source']

        try:
            starred = 'star' not in source or not source['star']
        except:
            logging.warn('Failed to star event, id "' + uuid_value + '" not found')
            raise KeyError('Could not find event id "' + uuid_value + '"')

        if starred:
            helper.db_util.update(id_value, index, {'star': True}, doc_type=doc_type)
            data['img'] = '/static/images/bookmarked.png'
        else:
            helper.db_util.update(id_value, index, {'star': False}, doc_type=doc_type)
            data['img'] = '/static/images/notbookmarked.png'

        return jsonify.dumps(data)
