from flask import Flask, render_template, request
import logging
import os
import json
from utils.efetch_helper import EfetchHelper

DEFAULTS = {'index': '*'}

def create_app(elastic_url, cache_directory, max_file_size, plugins_file, debug):
    """Creates the core efetch flask app"""
    app = Flask(__name__, static_path=u'/static')

    if debug:
        logging.basicConfig(level=logging.DEBUG)

    max_file_size_in_bytes = max_file_size * 1000000,

    make_cache_directories(cache_directory)

    # Log a warning if plugin file is missing
    if not os.path.isfile(plugins_file):
        logging.warn(u'Plugin config file "' + plugins_file + u'" is empty')

    _helper = EfetchHelper(get_current_directory(), cache_directory, max_file_size_in_bytes, plugins_file, elastic_url)

    @app.route('/')
    def home():
        """Returns the home page for efetch."""
        return render_template(u'index.html')

    @app.route('/plugins')
    @app.route('/plugins/')
    def list_plugins():
        """Returns a list of all active efetch plugins"""
        return json.dumps(_helper.plugin_manager.get_all_plugins())

    @app.route('/plugins/<plugin_name>', methods=['GET', 'POST'])
    def plugins(plugin_name):
        """Returns page of the given plugin.

        Args:
            plugin_name (str): The name of the plugin as defined in the yapsy-plugin file
        """
        plugin = _helper.plugin_manager.get_plugin_by_name(str(plugin_name).lower())

        index = _helper.get_request_value(request, 'index', DEFAULTS['index'])
        encoded_pathspec = _helper.get_request_value(request, 'pathspec', '')
        if not encoded_pathspec:
            encoded_pathspec = _helper.pathspec_helper.get_encoded_pathspec(os.path.expanduser('~'))

        logging.info('Plugin called %s, with index=%s and pathspec=%s', plugin_name, index, encoded_pathspec)

        efetch_dictionary = _helper.pathspec_helper.get_evidence_item(encoded_pathspec, index, plugin.cache,
                                                                      hasattr(plugin, 'fast') and plugin.fast)

        return plugin.get(efetch_dictionary, _helper, efetch_dictionary['file_cache_path'], request)

    return app


def get_current_directory():
    """Returns the current directory of this file"""
    return os.path.dirname(os.path.realpath(__file__))


def make_cache_directories(cache_directory):
    """Creates the cache directories if they do not exist"""
    if not os.path.isdir(cache_directory):
        try:
            os.mkdir(cache_directory)
            os.mkdir(cache_directory + os.path.sep + u'thumbnails')
            os.mkdir(cache_directory + os.path.sep + u'files')
        except IOError:
            logging.error(u'Could not find nor create output directory ' + cache_directory)
            raise IOError(u'Could not find nor create cache directory ' + cache_directory)