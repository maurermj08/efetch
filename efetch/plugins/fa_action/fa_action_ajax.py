"""
API for running a single plugin against multiple pathspecs
"""

import copy
import logging
import thread
import uuid
from bottle import abort
from yapsy.IPlugin import IPlugin


class SimpleRequest(object):
    """Pseudo Request object to pass to plugins"""
    pass


class FaActionAjax(IPlugin):

    def __init__(self):
        self.display_name = 'Action AJAX'
        self.popularity = 0
        self.cache = False
        self.fast = True
        self._actions = {}
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
        method = helper.get_request_value(request, 'method', '')

        if not method:
            abort(400, 'Method parameter required, but none found')

        if method == 'start':
            action_id = uuid.uuid4().hex
            plugin = helper.get_request_value(request, 'plugin', '')
            if not plugin:
                abort(400, 'Method START requires a plugin, but none found')
            self._actions[action_id] = {'action_id': action_id,
                                        'status': 'starting',
                                        'plugin': plugin,
                                        'success': 0,
                                        'fail': 0,
                                        'current': 0.,
                                        'percent': '0'}
            pseudo_request = SimpleRequest()
            pseudo_request.query = copy.deepcopy(request.query)
            pseudo_request.forms = copy.deepcopy(request.forms)
            thread.start_new_thread(self.action, (evidence, helper, pseudo_request, action_id))
        elif method == 'status':
            action_id = helper.get_request_value(request, 'action_id', '')
            if not action_id:
                return self._actions
            if action_id not in self._actions:
                abort(404, 'No action "' + str(action_id) + '" found')
        else:
            abort(404, 'No method "' + method + '"')

        return self._actions[action_id]

    def action(self, evidence, helper, request, action_id):
        """Runs a single plugin against multiple pathspecs"""
        index = helper.get_request_value(request, 'index', False)
        size = helper.get_request_value(request, 'size', 10000)
        sort = helper.get_request_value(request, 'sort', False)
        order = helper.get_request_value(request, 'order', 'asc')

        if not index:
            self._actions[action_id]['status'] = "Action plugin requires an index, but none found"

        # Get Plugin Object
        plugin = helper.plugin_manager.getPluginByName(str(self._actions[action_id]['plugin']).lower())
        if not plugin:
            self._actions[action_id]['status'] = "Failed: Could not find plugin " \
                                                 + str(self._actions[action_id]['plugin']).lower()
        plugin_object = plugin.plugin_object

        # Get Events
        query_body = helper.get_filters(request)
        query_body['size'] = size
        if sort:
            query_body['sort'] = {sort: order}
        events = helper.db_util.elasticsearch.search(index=index, doc_type='plaso_event', body=query_body)
        self._actions[action_id]['total'] = min(events['hits']['total'], int(size))
        self._actions[action_id]['status'] = 'active'

        # Run Events
        # TODO Add try catch for running individual plugin
        for item in events['hits']['hits']:
            source = item['_source']
            if 'pathspec' not in source:
                logging.warn('Missing pathspec, skipping document ' + item['_id'])
                self._actions[action_id]['current'] += 1.
                self._actions[action_id]['fail'] += 1
            else:
                efetch_dictionary = helper.get_efetch_dictionary(source['pathspec'], index, plugin_object.cache,
                                          hasattr(plugin_object, 'fast') and plugin_object.fast)
                efetch_dictionary['_id'] = item['_id']
                efetch_dictionary['doc_type'] = item['_type']
                plugin_object.get(efetch_dictionary, helper, efetch_dictionary['file_cache_path'], request)
                self._actions[action_id]['current'] += 1.
                self._actions[action_id]['success'] += 1
                self._actions[action_id]['percent']\
                    = "{0:.0f}%".format(self._actions[action_id]['current']/self._actions[action_id]['total'] * 100)

        self._actions[action_id]['status'] = 'done'