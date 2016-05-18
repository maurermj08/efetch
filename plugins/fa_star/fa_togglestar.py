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

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        data = {}

        # This value is the UUID which is returned so that the site knows what image to update
        data['img_id'] = helper.get_request_value(request, 'image_id', False)
        starred = False

        if not data['img_id'] or data['img_id'] == evidence['uuid']:
            data['img_id'] = evidence['uuid']
            starred = 'star' not in evidence or not evidence['star']
        else:
            event = helper.db_util.elasticsearch.get(index='efetch_evidence_' + evidence['image_id'], doc_type='event',
                                                     id=data['img_id'])
            try:
                starred = 'star' not in event['_source'] or not event['_source']['star']
            except:
                print('HERE: ' + str(event))
                logging.warn('Failed to star event, uuid "' + data['img_id'] + '" not found')
                abort(404, 'Could not find event')

        if starred:
            helper.db_util.update(data['img_id'], evidence['image_id'], {'star': True})
            data['img'] = '/resources/images/bookmarked.png'
        else:
            helper.db_util.update(data['img_id'], evidence['image_id'], {'star': False})
            data['img'] = '/resources/images/notbookmarked.png'

        return json.dumps(data)
