from flask import Flask, render_template, request
import logging
import os
import json
import uuid
from utils.efetch_helper import EfetchHelper
from werkzeug.utils import secure_filename

DEFAULTS = {'index': '*'}

def create_app(elastic_url, cache_directory, max_file_size, plugins_file, default_path, debug):
    """Creates the core efetch flask app"""
    app = Flask(__name__, static_url_path=u'/static')

    if debug:
        logging.basicConfig(level=logging.DEBUG)

    max_file_size_in_bytes = max_file_size * 1000000,

    make_cache_directories(cache_directory)

    # Log a warning if plugin file is missing
    if not os.path.isfile(plugins_file):
        logging.warn(u'Plugin config file "' + plugins_file + u'" is empty')

    _helper = EfetchHelper(get_current_directory(), cache_directory, max_file_size_in_bytes, plugins_file, elastic_url, default_path)

    @app.route('/', methods=['GET','POST'])
    def home():
        """Returns the home page for efetch and handles file uploads"""
        if request.method == 'POST':
            if 'file' not in request.files:
                logging.warn(u'No file attached to the upload')
                return render_template(u'index.html')
            
            file = request.files['file']
            # if user does not select file, browser also
            # submit an empty part without filename
            if file.filename == '':
                logging.warn(u'No file attached to the upload')
                return render_template(u'index.html')
            
            if file:
                upload_uuid = uuid.uuid4().hex
                upload_cache_directory = cache_directory + os.path.sep + u'uploads' + os.path.sep + upload_uuid
                os.mkdir(upload_cache_directory)
                filename = secure_filename(file.filename)
                upload_cache_path = os.path.join(upload_cache_directory, filename)
                file.save(upload_cache_path)
                pathspec = _helper.pathspec_helper.get_encoded_pathspec(upload_cache_path)
                new_evidence = _helper.pathspec_helper.get_evidence_item(pathspec,
                                                                         _helper.get_request_value(request, 'index', '*'),
                                                                         False,
                                                                         False)
                plugin = _helper.plugin_manager.get_plugin_by_name('analyze')
                return plugin.get(new_evidence, _helper, filename, request)

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
            encoded_pathspec = _helper.pathspec_helper.get_encoded_pathspec(os.path.expanduser(_helper.get_default_path()))

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
            os.mkdir(cache_directory + os.path.sep + u'uploads')
        except IOError:
            logging.error(u'Could not find nor create cache directory ' + cache_directory)
            raise IOError(u'Could not find nor create cache directory ' + cache_directory)
