import argparse
import json
import logging
import os
import sys
from bottle import Bottle, request, static_file, abort
from utils.dfvfs_util import DfvfsUtil
from utils.efetch_helper import EfetchHelper


class Efetch(object):
    def __init__(self, argv, address, port, debug, cache_dir, max_file_size):
        """Initializes Efetch variables and utils.
        
        Args:
            argv ([str]): A list of system arguments
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
            except:
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
        self._app.route('/plugins/<args:path>', method='GET', callback=self._plugins)
        self._app.route('/plugins/<args:path>', method='POST', callback=self._plugins)

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

    def _plugins(self, args):
        """Returns the iframe of the given plugin for the given file.

        Args:
            args (str): A path of plugins optionally followed by an image id
                and a file path
        
        Examples:
            /parent_plugin1/parent_plugin2/child_plugin/image_id/path/to/file
            /parent_plugin1/child_plugin/?some_variable=some_value
            /child_plugin/image_id/
            /child_plugin/
        """
        logging.info('Plugin called "%s"', args)
        args_list = args.split('/')

        name = str(args_list.pop(0))
        plugin = self._helper.plugin_manager.getPluginByName(str(name).lower())

        if not plugin:
            abort(404, "Sorry, could not find plugin " + str(name).lower())

        evidence = None
        file_cache_path = None
        children = None

        if plugin.plugin_object.parent:
            children = '/'.join(args_list)
            # Updates the args list so parent plugins can get imaged_id, and path
            while (args_list and self._helper.plugin_manager.getPluginByName(args_list[0]) and
                    self._helper.plugin_manager.getPluginByName(args_list[0]).plugin_object.parent):
                args_list.pop(0)
            if args_list and self._helper.plugin_manager.getPluginByName(args_list[0]):
                args_list.pop(0)

        #TODO NEW
        index = self._helper.get_request_value(request, 'index', 'efetch_evidence*')
        query = self._helper.get_query(request)

        #print("HERE... Index=", index, " Query=", str(query))
        if '_a' in request.query:
            query = self._helper.get_query(request)
            evidence = self._helper.db_util.get_sources(self._helper.db_util.query_index({'query': query}, index, 1),
                                                        True)
        elif args_list:
            pid = '/'.join(args_list)
            print('HERE:' + str(pid))
            evidence =  self._helper.db_util.get_file_from_pid(pid)
        else:
            logging.warn('No PID or Query specified')

        #print("HERE... Evidence=", str(evidence))

        if plugin.plugin_object.cache:
            file_cache_path = self._helper.cache_file(evidence)

        # Get Mimetype if file is cached else guess Mimetype
        if file_cache_path and 'mimetype' not in evidence:
            evidence['mimetype'] = self._helper.get_mimetype(file_cache_path)
            update = {'mimetype': evidence['mimetype']}
            self._helper.db_util.update(evidence['uuid'], evidence['image_id'], update)
        elif 'mimetype' not in evidence:
            evidence['mimetype'] = self._helper.guess_mimetype(evidence['ext'])
        # Remove Failed Cache
        elif file_cache_path and not evidence['mimetype']:
            os.remove(file_cache_path)
            evidence['mimetype'] = self._helper.get_mimetype(file_cache_path)
            update = {'mimetype': evidence['mimetype']}
            self._helper.db_util.update(evidence['uuid'], evidence['image_id'], update)
        
        # Return plugins frame
        return plugin.plugin_object.get(evidence, self._helper,
                file_cache_path, request, children)

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
    efetch = Efetch(sys.argv[1:], args.address, args.port, args.debug, args.cache, args.maxfilesize)
    efetch.start()
