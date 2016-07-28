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


import argparse
import json
import logging
import os
import sys
from bottle import Bottle, request, static_file, abort
from utils.efetch_helper import EfetchHelper


class Efetch(object):
    def __init__(self, address, port, debug, cache_dir, max_file_size):
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

        curr_dir = os.path.dirname(os.path.realpath(__file__))
        output_dir = cache_dir
        upload_dir = curr_dir + os.path.sep + u'uploads' + os.path.sep

        if debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        if not output_dir.endswith(os.path.sep):
            output_dir += os.path.sep
        if not os.path.isdir(output_dir):
            try:
                os.mkdir(output_dir)
                os.mkdir(output_dir + os.path.sep + 'thumbnails')
                os.mkdir(output_dir + os.path.sep + 'files')
            except IOError:
                logging.error(u'Could not find nor create output directory ' + output_dir)
                sys.exit(2)

        self._helper = EfetchHelper(curr_dir, output_dir, upload_dir, max_file_size * 1000000)

        self._route()

    def start(self):
        """Starts the Bottle server."""
        self._app.run(host=self._address, port=self._port, server='cherrypy')

    def _route(self):
        """Applies the routes to Efetch methods."""
        self._app.route('/', method='GET', callback=self._index)
        self._app.route('/resources/<resource_path:path>',
                        method='GET', callback=self._get_resource)
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

    def _index(self):
        """Returns the home page for Efetch."""
        return self._get_resource('cases_table.html')

    def _list_plugins(self):
        """Returns a json object of all the plugins."""
        plugin_list = []

        for plugin in self._helper.plugin_manager.getAllPlugins():
            plugin_list.append(plugin.name)

        return json.dumps(plugin_list)

    def _plugins(self, plugin_name):
        """Returns the iframe of the given plugin for the given file.

        Args:
            plugin_name (str): The name of the plugin as defined in the yapsy-plugin file
        """
        plugin = self._helper.plugin_manager.getPluginByName(str(plugin_name).lower())

        if not plugin:
            abort(404, "Could not find plugin " + str(plugin_name).lower())

        index = self._helper.get_request_value(request, 'index', 'case*')
        encoded_pathspec = self._helper.get_request_value(request, 'pathspec', '')

        logging.info('Plugin called %s, with index=%s and pathspec=%s', plugin_name, index, encoded_pathspec)
        logging.debug('Query String = %s', self._helper.get_query_string(request))

        if '_a' in request.query:
            query = self._helper.get_query(request)
        else:
            query = {'match_all': {}}

        if not encoded_pathspec:
            encoded_pathspec = self._helper.db_util.query_sources(
                {'query': query}, index, 1)['pathspec']

        efetch_dictionary = self._helper.\
            get_efetch_dictionary(encoded_pathspec, index, plugin.plugin_object.cache,
                                  hasattr(plugin.plugin_object, 'fast') and plugin.plugin_object.fast)
        
        # Return plugins frame
        return plugin.plugin_object.get(efetch_dictionary, self._helper, efetch_dictionary['file_cache_path'], request)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(u'-a', u'--address',
                        help=u'the IP address or hostname this server runs on',
                        action=u'store',
                        default=u'0.0.0.0')
    parser.add_argument(u'-p', u'--port', type=str,
                        help=u'the port this servers runs on',
                        action=u'store',
                        default=8080)
    parser.add_argument(u'-d', u'--debug',
                        help=u'displays debug output',
                        action=u'store_true')
    parser.add_argument(u'-c', u'--cache', type=str,
                        help=u'the directory to stored cached files',
                        action=u'store',
                        default=os.path.dirname(os.path.realpath(__file__)) + os.path.sep + u'cache' + os.path.sep)
    parser.add_argument(u'-m', u'--maxfilesize', type=int,
                        help=u'the max file size allowed to be cached in Megabytes',
                        action=u'store',
                        default=10000)
    args = parser.parse_args()
    efetch = Efetch(args.address, args.port, args.debug, args.cache, args.maxfilesize)
    efetch.start()
