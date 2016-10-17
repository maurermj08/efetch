# Copyright 2016 Michael J Maurer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import os
import sys
from bottle import Bottle, request, static_file
from rocket import Rocket
from threading import Thread
from utils.efetch_helper import EfetchHelper


class Efetch(object):
    def __init__(self, address, port, elastic_url, debug, cache_dir, max_file_size, plugins_file):
        """Initializes Efetch variables and utils.

        Args:
            address: The hostname or IP address to listen on
            port: The port number the server is running on
            debug: The boolean that enables debug logging
            cache_dir: The directory to cache temporary files
            max_file_size: The max file size in Megabytes to cache
        """
        self._address = address
        self._port = port
        self._helper = None
        self._app = Bottle()
        self._debug = debug
        self._curr_directory = os.path.dirname(os.path.realpath(__file__))
        output_dir = cache_dir

        if debug:
            logging.basicConfig(level=logging.DEBUG)
            logging.getLogger(u'Rocket').setLevel(logging.WARNING)
        else:
            logging.basicConfig(level=logging.INFO)

        if not output_dir.endswith(os.path.sep):
            output_dir += os.path.sep
        if not os.path.isdir(output_dir):
            try:
                os.mkdir(output_dir)
                os.mkdir(output_dir + os.path.sep + u'thumbnails')
                os.mkdir(output_dir + os.path.sep + u'files')
            except IOError:
                logging.error(u'Could not find nor create output directory ' + output_dir)
                sys.exit(2)

        if not os.path.isfile(plugins_file):
            logging.warn(u'Plugin config file "' + plugins_file + u'" is empty')

        self._helper = EfetchHelper(self._curr_directory, output_dir,
                                    max_file_size * 1000000, plugins_file, elastic_url)

        self._route()

    def start(self):
        """Starts the Bottle server."""
        rocket = Rocket((self._address, self._port), 'wsgi', {'wsgi_app': self._app})
        server_thread = Thread(target=rocket.start, name='_rocket')
        server_thread.start()

        try:
            while server_thread.is_alive():
                server_thread.join(5)
        except (KeyboardInterrupt, SystemExit):
            self._helper.poll.stop = True
            rocket.stop()

    def _route(self):
        """Applies the routes to Efetch methods."""
        self._app.route('/', method='GET', callback=self._index)
        self._app.route('/favicon.ico', method='GET', callback=self._get_favicon)
        self._app.route('/resources/<resource_path:path>',
                        method='GET', callback=self._get_resource)
        self._app.route('/plugins', method='GET', callback=self._list_plugins)
        self._app.route('/plugins/', method='GET', callback=self._list_plugins)
        self._app.route('/plugins/<plugin_name>', method='GET', callback=self._plugins)
        self._app.route('/plugins/<plugin_name>', method='POST', callback=self._plugins)

    def _get_resource(self, resource_path):
        """Returns any file in the resource directory.

        Args:
            resource_path (str): Path to the resource starting at the resource directory.

        """
        full_path = self._helper.resource_dir + resource_path
        res_dir = os.path.dirname(full_path)
        res_name = os.path.basename(full_path)
        return static_file(res_name, root=res_dir)

    def _get_favicon(self):
        """Returns the favicon"""
        return self._get_resource('favicon.ico')

    def _index(self):
        """Returns the home page for Efetch."""
        return self._get_resource(u'index.html')

    def _list_plugins(self):
        """Returns a json object of all the plugins."""
        return json.dumps(self._helper.plugin_manager.get_all_plugins())

    def _plugins(self, plugin_name):
        """Returns the iframe of the given plugin for the given file.

        Args:
            plugin_name (str): The name of the plugin as defined in the yapsy-plugin file
        """
        plugin = self._helper.plugin_manager.get_plugin_by_name(str(plugin_name).lower())

        index = self._helper.get_request_value(request, 'index', '*')
        encoded_pathspec = self._helper.get_request_value(request, 'pathspec', '')
        if not encoded_pathspec and self._helper.get_request_value(request, 'method', '') == 'Browse':
            encoded_pathspec = self._helper.pathspec_helper.get_encoded_pathspec(os.path.expanduser('~'))

        logging.info('Plugin called %s, with index=%s and pathspec=%s', plugin_name, index, encoded_pathspec)
        logging.debug('Query String = %s', self._helper.get_query_string(request))

        if '_a' in request.query:
            query = self._helper.get_query(request)
        else:
            query = {'exists': {'field': 'pathspec'}}

        if not encoded_pathspec.strip():
            encoded_pathspec = self._helper.db_util.query_sources(
                {'query': query}, index, 1)['pathspec']


        efetch_dictionary = self._helper.pathspec_helper. \
            get_evidence_item(encoded_pathspec, index, plugin.cache, hasattr(plugin, 'fast') and plugin.fast)

        # Return plugins
        if self._debug:
            return plugin.get(efetch_dictionary, self._helper, efetch_dictionary['file_cache_path'], request)
        else:
            try:
                results = plugin.get(efetch_dictionary, self._helper, efetch_dictionary['file_cache_path'], request)
            except:
                results = plugin.get(efetch_dictionary, self._helper, efetch_dictionary['file_cache_path'], request)
            return results