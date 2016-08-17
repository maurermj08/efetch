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
import platform
import yaml
from bottle import abort, static_file
from jinja2 import Template
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
                return yaml.load(stream)
            except yaml.YAMLError as exc:
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
            abort(404, u'Could not find plugin "' + name + u'"')
        elif not plugin:
            plugin = self.config_file_plugins[name]
            return Plugin(plugin.get('name', 'None'),
                          plugin.get('description', 'None'),
                          plugin.get('cache', True),
                          plugin.get('popularity', 5),
                          plugin.get('fast', False),
                          map(str.lower, plugin.get('mimetypes', [])),
                          map(str.lower, plugin.get('extensions', [])),
                          map(str.lower, plugin.get('os', [])),
                          plugin.get('command', False),
                          plugin.get('format', 'Text'),
                          plugin.get('file', False))
        else:
            return plugin.plugin_object





class Plugin(object):
    """Simple dynamically created plugin object"""

    def __init__(self, display_name, description, cache, popularity, fast, mimetypes,
                 extensions, operating_systems, command, format, file):
        self.display_name = display_name
        self.description = description
        self.popularity = popularity
        self.cache = cache
        self.fast = fast
        self._mimetypes = mimetypes
        self._extensions = extensions
        self._operating_systems = operating_systems
        self._command = command
        self._format = format
        self._file = file

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
        if self._command:
            command = Template(self._command).render(evidence)
            process = os.popen(command)
            command_output = process.read()
            process.close()

        if self._file:
            file_name = Template(self._file).render(evidence)
            return static_file(os.path.basename(file_name), root=os.path.dirname(file_name))

        # TODO Use different formats
        return u'<p style="font-family:Courier New, Courier, monospace;">' \
               + unicode(command) + u'</p><hr><xmp>' + unicode(command_output, errors='ignore') + u'</xmp>'