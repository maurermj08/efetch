"""
Basic UI for browsing and analyzing files
"""

from yapsy.IPlugin import IPlugin
from flask import render_template
import logging

class Analyze(IPlugin):
    def __init__(self):
        self.display_name = 'File Analyze'
        self.popularity = 0
        self.category = 'misc'
        self.cache = False
        self.fast = False
        self.action = False
        self.ignore_loader = ['preview', 'fa_timeline']
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
        """Provides a web view with all applicable plugins, defaults to most popular"""

        if evidence['meta_type'] =='File' and not evidence['mimetype_known']:
            evidence['mimetype'] = helper.pathspec_helper.get_mimetype(evidence['pathspec'])
            evidence['mimetype_known'] = True

        # Add Directoy link
        plugins = []
        other_plugins = {}

        size = evidence.get('size', 0)
        if isinstance(size, list):
            size = size[0]

        # Order Plugins by populatiry from highest to lowest
        for pop in reversed(range(1, 11)):
            for plugin_name in helper.plugin_manager.get_all_plugins():
                plugin = helper.plugin_manager.get_plugin_by_name(plugin_name)
                if plugin.popularity == pop:
                    # Check if plugin applies to curr file
                    if plugin.display_name != 'Overview' and \
                            plugin.check(evidence, evidence['file_cache_path']) and \
                            (not plugin.cache or int(size) <= helper.max_file_size):
                        logging.debug("Check matched, adding plugin " + plugin.display_name)
                        plugins.append({
                           'icon': getattr(plugin, 'icon', 'fa-file-o'),
                           'name': plugin_name,
                           'display_name': getattr(plugin, 'display_name', plugin_name)
                        })
                    elif plugin.display_name != 'Overview':
                        category = getattr(plugin, 'category', 'misc').lower()
                        if not category in other_plugins:
                            other_plugins[category] = []
                        other_plugins[category].append({
                           'icon': getattr(plugin, 'icon', 'fa-file-o'),
                           'category': category,
                           'name': plugin_name,
                           'display_name': getattr(plugin, 'display_name', plugin_name)
                        })
                        logging.debug("Check did not match, NOT adding plugin to matched " + plugin_name)

        theme = 'black'
        home = '/plugins/overview?' + evidence['url_query']

        # Modifies HTML
        return render_template('analyze.html', evidence=evidence, theme=theme, plugins=plugins, 
                other_plugins=other_plugins, home=home)
