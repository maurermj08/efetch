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


import logging
import os
import glob
import platform
import oyaml
from jinja2 import Template
from flask import send_from_directory
from flask import render_template
from flask import redirect
from flask import url_for
from werkzeug.utils import secure_filename
from yapsy.PluginManager import PluginManager


class EfetchPluginManager(object):
    """This class manages and creates plugin objects"""

    def __init__(self, plugins_file, curr_directory):
        # Plugin Manager Setup
        self.plugin_manager = PluginManager()
        self.plugin_manager.setPluginPlaces([curr_directory + u'/plugins/'])
        self.plugins_file = plugins_file
        self.reload_plugins()

    def reload_plugins_file(self):
        """Reloads all plugins from the YAML file"""
        self.config_file_plugins = self.load_plugin_config(self.plugins_file)

    def reload_plugins(self):
        """Reloads all Yapsy and YAML file plugins"""
        self.plugin_manager.collectPlugins()
        for plugin in self.plugin_manager.getAllPlugins():
            self.plugin_manager.activatePluginByName(plugin.name)
        self.reload_plugins_file()

    def load_plugin_config(self, plugins_file):
        """Loads the plugin config file"""
        if not os.path.isfile(plugins_file):
            logging.warn(u'Could not find Plugin Configuration File "' + plugins_file + u'"')
            return {}

        with open(plugins_file, 'r') as stream:
            try:
                return oyaml.load(stream)
            except oyaml.YAMLError as exc:
                logging.error(u'Failed to parse Plugin Configuration File')
                logging.error(exc)

        return {}

    def get_all_plugins(self):
        """Gets a list of all the plugins"""
        plugins = []

        for plugin in self.plugin_manager.getAllPlugins():
            plugins.append(plugin.name)
        for key in self.config_file_plugins:
            plugins.append(key)

        return plugins

    def get_plugin_by_name(self, name):
        """Gets an Efetch plugin by name"""
        plugin = self.plugin_manager.getPluginByName(str(name).lower())
        if not plugin and name not in self.config_file_plugins:
            logging.warn(u'Request made for unknown plugin "' + name + u'"')
        elif not plugin:
            plugin = self.config_file_plugins[name]
            return Plugin(plugin.get('name', 'None'),
                          plugin.get('description', 'None'),
                          plugin.get('cache', True),
                          plugin.get('popularity', 6),
                          plugin.get('fast', False),
                          plugin.get('store', False),
                          map(str.lower, plugin.get('mimetypes', [])),
                          map(str.lower, plugin.get('extensions', [])),
                          map(str.lower, plugin.get('os', [ 'linux' ])),
                          plugin.get('command', False),
                          plugin.get('format', 'Text'),
                          plugin.get('file', False),
                          plugin.get('openwith', False),
                          plugin.get('icon', 'fa-file-o'),
                          plugin.get('category', 'misc').lower(),
                          plugin.get('display', 'xmp').lower(),
                          plugin.get('inputs', False))
        else:
            return plugin.plugin_object


class Plugin(object):
    """Simple dynamically created plugin object"""

    def __init__(self, display_name, description, cache, popularity, fast, store, mimetypes, extensions,
                 operating_systems, command, format, file, openwith, icon, category, display, inputs):
        self.display_name = display_name
        self.description = description
        self.popularity = popularity
        self.cache = cache
        self.fast = fast
        self.action = bool(store)
        self.icon = icon
        self.category = category
        self._store = store
        self._mimetypes = mimetypes
        self._extensions = extensions
        self._operating_systems = operating_systems
        self._command = command
        self._format = format
        self._file = file
        self._openwith = openwith
        self._display = display
        self._inputs = inputs

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        if self._operating_systems and platform.system().lower() not in self._operating_systems:
            return False

        if 'meta_type' in evidence and evidence['meta_type'] != 'File':
            return False

        if self._mimetypes and not str(evidence['mimetype']).lower() in self._mimetypes:
            return False

        if self._extensions and not str(evidence['extension']).lower() in self._extensions:
            return False

        return True

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        if self._inputs and request.method == 'GET':
            return render_template('input.html', inputs=self._inputs, pathspec=evidence['pathspec'], openwith=self._openwith)
        elif self._inputs and request.method == 'POST':
            for key in request.form:
                if key not in evidence:
                    evidence[key] = secure_filename(request.form[key])
                else:
                    logging.warn('Key conflict in input, bad key "' + key + '"')

        evidence['plugin_command'] = Template(self._command).render(evidence)

        if self._command:
            if self._store:
                output = helper.action_get(evidence, request, self.display_name, self.run_command, self._store)
            else:
                output = self.run_command(evidence, helper)

        if self._file:
            file_name = str(Template(self._file).render(evidence))
            if os.path.isfile(file_name):
                file_name = file_name
            elif not os.path.isdir(file_name):
                file_name = glob.glob(file_name)
                if isinstance(file_name, list):
                    file_name = file_name[0]

            if self._openwith:
                # TODO Figure out if this is the best method, because it may result in duplicate caching
                # TODO remove any reference to evidence['cache_path'] and instead always use path on disk
                new_pathspec = helper.pathspec_helper.get_encoded_pathspec(file_name)
                plugin = helper.plugin_manager.get_plugin_by_name(self._openwith)
                new_evidence = helper.pathspec_helper.get_evidence_item(new_pathspec,
                                                                        helper.get_request_value(request, 'index', '*'),
                                                                        False,
                                                                        hasattr(plugin, 'fast') and plugin.fast)
                return plugin.get(new_evidence, helper, file_name, request)
            else:
                return send_from_directory(os.path.dirname(file_name), os.path.basename(file_name))

        # TODO - should this use case even be allowed?
        if not self._command:
            return ''

        # TODO Use different formats\
        # TODO Verify this unicode is accurate, appears to error on blank strings

        try:
            output_string = unicode(output, errors='ignore')
        except:
            output_string = output

        if self._display == 'raw':
            results = output_string
        elif self._display == 'noheader': 
            results = render_template('plugin_noheader.html', output=output_string.split('\n')) 
        elif self._display == 'csv': 
            table = output_string.split('\n')
            header = table[0]
            body = table[1:]
            rows = []
            for line in body:
                rows.append(line.split(','))
            results = render_template('plugin_csv.html', header=header.split(','), rows=rows) 
        else:
            results = render_template('plugin_default.html', command=unicode(evidence['plugin_command']), output=output_string.split('\n')) 

        return results

    @staticmethod
    def run_command(evidence, helper):
        process = os.popen(evidence['plugin_command'])
        command_output = process.read()
        process.close()
        return command_output
