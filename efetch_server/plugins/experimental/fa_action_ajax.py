"""
API for running a single plugin against multiple pathspecs
"""

import copy
import elasticsearch
import logging
import multiprocessing
from multiprocessing.pool import ThreadPool
import threading
import thread
import traceback
import uuid
from bottle import abort
from yapsy.IPlugin import IPlugin


class SimpleRequest(object):
    """Pseudo Request object to pass to plugins"""
    pass

def _action_process(items, helper, request, action_id, plugin, index, check, _actions, action_lock):
    """Runs the specified plugin on the provided event items aka events[hits][hits]"""
    for item in items:
        try:
            source = item['_source']
            if 'pathspec' not in source:
                with action_lock:
                    _actions[action_id]['fail'] += 1
                    _actions[action_id]['errors'] += source['pathspec'] + '\nNot found in Elasticsearch'
            else:
                efetch_dictionary = helper.pathspec_helper.\
                    get_evidence_item(source['pathspec'], index, plugin.cache,
                                                            hasattr(plugin, 'fast') and plugin.fast)
                efetch_dictionary['_id'] = item['_id']
                efetch_dictionary['doc_type'] = item['_type']
                if not check or plugin.check(efetch_dictionary, efetch_dictionary['file_cache_path']):
                    plugin.get(efetch_dictionary, helper, efetch_dictionary['file_cache_path'], request)
                with action_lock:
                    _actions[action_id]['success'] += 1
        except Exception as e:
            with action_lock:
                _actions[action_id]['fail'] += 1
                _actions[action_id]['error'] += source['pathspec'] + '\n' +\
                                                e.message + '\n' + traceback.format_exc() + '\n\n'
        finally:
            with action_lock:
                _actions[action_id]['current'] += 1
                _actions[action_id]['percent'] = "{0:.0f}%".format(_actions[action_id]['current'] /
                                                               _actions[action_id]['total'] * 100)
                if _actions[action_id]['current'] == _actions[action_id]['total']:
                    _actions[action_id]['status'] = 'done'


class FaActionAjax(IPlugin):

    def __init__(self):
        self.display_name = 'Action AJAX'
        self.popularity = 0
        self.cache = False
        self.fast = True
        self.action = False
        self._actions = {}
        self._thread_pool_size = max([multiprocessing.cpu_count() - 1, 1])
        self._thread_pool = ThreadPool(processes=self._thread_pool_size)
        self._max_queue_size = 25
        self._max_size = 10000
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
                                        'percent': '0',
                                        'error': '',
                                        'total': 0}
            pseudo_request = SimpleRequest()
            pseudo_request.query = copy.deepcopy(request.query)
            pseudo_request.forms = copy.deepcopy(request.forms)
            thread.start_new_thread(self.start_action, (evidence, helper, pseudo_request, action_id))
        elif method == 'status':
            action_id = helper.get_request_value(request, 'action_id', '')
            if not action_id:
                return self._actions
            if action_id not in self._actions:
                abort(404, 'No action "' + str(action_id) + '" found')
        elif method == 'active_status':
            active_status = {}
            active_status['rows'] = []
            for key in self._actions:
                if self._actions[key]['status'] == 'active':
                    active_status['rows'].append(self._actions[key])
            active_status['total'] = len(active_status['rows'])
            return active_status
        elif method == 'done_status':
            done_status = {}
            done_status['rows'] = []
            for key in self._actions:
                if self._actions[key]['status'] == 'done':
                    done_status['rows'].append(self._actions[key])
            done_status['total'] = len(done_status['rows'])
            return done_status
        else:
            abort(404, 'No method "' + method + '"')

        return self._actions[action_id]


    def start_action(self, evidence, helper, request, action_id):
        """Runs a single plugin against multiple pathspecs"""
        index = helper.get_request_value(request, 'index', False)
        size = int(helper.get_request_value(request, 'size', self._max_size))
        sort = helper.get_request_value(request, 'sort', False)
        order = helper.get_request_value(request, 'order', 'asc')
        all = bool(helper.get_request_value(request, 'all', False))
        check = bool(helper.get_request_value(request, 'check', True))
        action_lock = threading.Lock()
        queue = []

        if not index:
            self._actions[action_id]['status'] = "Action plugin requires an index, but none found"

        # Get Plugin Object
        plugin = helper.plugin_manager.get_plugin_by_name(str(self._actions[action_id]['plugin']).lower())
        if not plugin:
            self._actions[action_id]['status'] = "Failed: Could not find plugin " \
                                                 + str(self._actions[action_id]['plugin']).lower()

        # Get Events
        query_body = helper.get_filters(request, [], [])
        if sort and not all:
            query_body['sort'] = {sort: order}

        if size > self._max_size or all:
            query_body['size'] = 0
            temp_events = [helper.db_util.elasticsearch.search(index=index, doc_type='plaso_event', body=query_body)]
            self._actions[action_id]['total'] = temp_events[0]['hits']['total']
            del query_body['size']
            events = elasticsearch.helpers.scan(helper.db_util.elasticsearch, query_body,
                                                scroll=u'240m', size=self._max_size)
            for item in events:
                with action_lock:
                    self._actions[action_id]['status'] = 'active'

                queue.append(item)
                if len(queue) >= self._max_queue_size:
                    self._thread_pool.apply_async(_action_process, args=(queue, helper, request, action_id,
                                                                         plugin, index, check,
                                                                         self._actions, action_lock))
                    queue = []
        else:
            query_body['size'] = size
            events = [helper.db_util.elasticsearch.search(index=index, doc_type='plaso_event', body=query_body)]
            self._actions[action_id]['total'] = min(events[0]['hits']['total'], int(size))

            for event in events:
                with action_lock:
                    self._actions[action_id]['status'] = 'active'

                # Run Events
                for item in event['hits']['hits']:
                    queue.append(item)
                    if len(queue) == self._max_queue_size:
                        self._thread_pool.apply_async(_action_process, args=(queue, helper, request, action_id,
                                                                             plugin, index, check,
                                                                             self._actions, action_lock))
                        queue = []

        if len(queue) > 0:
            self._thread_pool.apply_async(_action_process, args=(queue, helper, request, action_id, plugin,
                                                                 index, check, self._actions, action_lock))
