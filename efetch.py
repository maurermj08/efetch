import getopt
import json
import logging
import os
import sys
from bottle import Bottle, request, static_file, abort
from utils.efetch_helper import EfetchHelper

class Efetch(object):
    def __init__(self, argv):
        """Initializes Efetch variables and utils.
        
        Args:
            argv ([str]): A list of system arguments
        """
        try:
            opts, args = getopt.getopt(argv, "ha:p:o:s:dD:m:",
                    ["help", "address=", "port=", "output=", "size=", "debug", "maxfilesize="])
        except getopt.GetoptError:
            self.usage()
            sys.exit(2)

        self._address = "localhost"
        self._port = "8080"
        self._max_cache = 10000 #Megabytes
        self._max_download_size = 100 #Megabytes
        self._helper = None
        self._app = Bottle()

        curr_dir = os.path.dirname(os.path.realpath(__file__))
        output_dir = curr_dir + "/cache/"
        upload_dir = curr_dir + "/uploads/"
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)

        for opt, arg in opts:
            if opt in ("-h", "--help"):
                self.usage()
                sys.exit()
            elif opt in ("-a", "--address"):
                self._address = arg
            elif opt in ("-p", "--port"):
                self._port = str(arg)
            elif opt in ("-o", "--output"):
                self._output_dir = arg
            elif opt in ("-s", "--size"):
                self._max_cache = arg
            elif opt in ('-d', "--debug"):
                self._logging.basicConfig(level=logging.DEBUG)
            elif opt in ('-m', "--maxfilesize"):
                self._max_download_size = arg
            else:
                logging.error("Unknown argument " + opt)
                self.usage()
                sys.exit(2)

        if not output_dir.endswith("/"):
            output_dir = output_dir + "/"
        if not os.path.isdir(output_dir):
            logging.error("Could not find output directory " + output_dir)
            sys.exit(2)

        self._helper = EfetchHelper(curr_dir, output_dir, upload_dir, self._max_download_size * 1000000)

        self._route()

    def start(self):
        """Starts the Bottle server."""
        self._app.run(host=self._address, port=self._port)

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
        #TODO: Need better security
        if '..' in str(resource_path):
            return
        else:
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
        args_list = args.split('/')

        name = str(args_list.pop(0))
        plugin = self._helper.plugin_manager.getPluginByName(str(name).lower())

        if not plugin:
            abort(404, "Sorry, could not find plugin " + str(name).lower())

        evidence = None
        file_cache_path = None
        children = None

        if plugin.plugin_object.parent():
            children = '/'.join(args_list)
            #Updates the args list so parent plugins can get imaged_id,  and path
            while (args_list and self._helper.plugin_manager.getPluginByName(args_list[0]) and
                    self._helper.plugin_manager.getPluginByName(args_list[0]).plugin_object.parent()):
                args_list.pop(0)
            if args_list and self._helper.plugin_manager.getPluginByName(args_list[0]):
                args_list.pop(0)

        #Image ID
        if args_list:
            image_id = args_list.pop(0)
        else:
            image_id = None

        #Path
        if args_list:
            path = '/'.join(args_list)
        else:
            path = ''

        if image_id:
            #Get file from database
            try:
                evidence = self._helper.db_util.get_file(image_id, image_id + '/' + str(path))
            except:
                abort(404, 'File "' + str(path) + '" not found for image "' + image_id + '"')

            #Cache file
            if plugin.plugin_object.cache():
                file_cache_path = self._helper.cache_file(evidence)

            #Get Mimetype if file is cached else guess Mimetype
            if file_cache_path and 'mimetype' not in evidence:
                evidence['mimetype'] = self._helper.get_mimetype(file_cache_path)
                update = { 'mimetype' : evidence['mimetype'] }
                self._helper.db_util.update_by_ppid(evidence['pid'], update)
            elif 'mimetype' not in evidence:
                evidence['mimetype'] = self._helper.guess_mimetype(evidence['ext'])
        
        #Return plugins frame
        return plugin.plugin_object.get(evidence, self._helper,
                file_cache_path, request, children)

    def usage(self):
        """Usage string for Efetch command line"""
        print("usage: efetch.py [-h] [-a ADDRESS] [-p PORT] [-o DIR ] [-s SIZE] [-d] [-D DATABASE] [-m maxfilesize]")
        print("")
        print("efetch is a simple webserver that can return files and thumbnails from an image.")
        print("!!!WARNING!!! there are major known security issues if this is run as root and externally facing!")
        print("")
        print("optional arguments:")
        print("  -h, --help         shows this help message and exits")
        print("  -a, --address      sets the IP address or hostname this server runs on, defaults to localhost")
        print("  -p, --port         sets the port this server runs on, defaults to 8080")
        print("  -o, --output       directory to store output files")
        print("  -s, --size         the max size of cache storage, defaults to 1GB [NOT IMPLEMENTED]")
        print("  -d, --debug        displays debug output")
        print("  -D, --database     use an existing database file")
        print("  -m, --maxfilesize  max file size to download when caching files")
        print("")

if __name__=="__main__":
    efetch = Efetch(sys.argv[1:])
    efetch.start()
