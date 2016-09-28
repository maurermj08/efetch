"""
Basic UI for browsing and analyzing files
"""

from yapsy.IPlugin import IPlugin
import os
import logging


class Analyze(IPlugin):
    def __init__(self):
        self.display_name = 'File Analyze'
        self.popularity = 0
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

        # Add Directoy link
        plugins = []
        plugins.append(
            '<a href="/plugins/overview?' + evidence['url_query']
            + '" target="frame">Overview</a><br>')

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
                        plugins.append('<a href="/plugins/' + plugin_name + '?' + evidence['url_query']
                                       + '" target="frame">' + plugin.display_name + '</a><br>')
                    else:
                        logging.debug("Check did not match, NOT adding plugin " + plugin.display_name)

        # Modifies HTML page
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/analyze_template.html', 'r')
        html = str(template.read())
        template.close()
        html = html.replace('<!-- Home -->', "/plugins/overview?" + evidence['url_query'])

        if evidence['meta_type'] == 'Directory':
            html = html.replace('<!-- File -->', evidence['file_name'])
            html = html.replace('<!-- Mimetype -->', 'Directory')
            if 'file_size' in evidence:
                html = html.replace('<!-- Size -->', str(evidence['size']) + " Bytes")
            else:
                html = html.replace('<!-- Size -->', "0 Bytes")
            html = html.replace('<!-- Links -->', "\n".join(plugins))
        else:
            html = html.replace('<!-- File -->', evidence['file_name'])
            html = html.replace('<!-- Mimetype -->', evidence['mimetype'])
            html = html.replace('<!-- Size -->', str(size) + " Bytes")
            html = html.replace('<!-- Links -->', "\n".join(plugins))

        return html
