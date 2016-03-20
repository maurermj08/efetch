"""
Basic UI for browsing and analyzing files
"""

from yapsy.IPlugin import IPlugin
import os
import logging


class FaAnalyze(IPlugin):
    def __init__(self):
        self.display_name = 'File Analyze'
        self.popularity = 0
        self.parent = False
        self.cache = True
        self.ignore_loader = ['fa_preview']
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children):
        """Provides a web view with all applicable plugins, defaults to most popular"""

        # Add Directoy link
        plugins = []
        plugins.append(
            '<a href="/plugins/fa_loader/fa_overview/' + evidence['pid'] + '" target="frame">Overview</a><br>')

        if not evidence['mimetype']:
            mimetype = helper.guess_mimetype(evidence['ext'])
        else:
            mimetype = evidence['mimetype']

        size = evidence.get('file_size', [0])[0]

        # Order Plugins by populatiry from highest to lowest
        for pop in reversed(range(1, 11)):
            for plugin in helper.plugin_manager.getAllPlugins():
                if plugin.plugin_object.popularity == pop:
                    # Check if plugin applies to curr file
                    if plugin.plugin_object.display_name != 'Overview' and plugin.plugin_object.check(evidence,
                                                                                                       path_on_disk):
                        logging.debug("Check matched, adding plugin " + plugin.plugin_object.display_name)
                        if plugin.name not in self.ignore_loader:
                            plugins.append('<a href="/plugins/fa_loader/' + plugin.name + '/' + evidence[
                                'pid'] + '" target="frame">' + plugin.plugin_object.display_name + '</a><br>')
                        else:
                            plugins.append('<a href="/plugins/' + plugin.name + '/' + evidence[
                                'pid'] + '" target="frame">' + plugin.plugin_object.display_name + '</a><br>')
                    else:
                        logging.debug("Check did not match, NOT adding plugin " + plugin.plugin_object.display_name)

        # Modifies HTML page
        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/analyze_template.html', 'r')
        html = str(template.read())
        template.close()
        html = html.replace('<!-- Home -->', "/plugins/fa_loader/fa_overview/" + evidence['pid'])

        if evidence['meta_type'] == 'Directory':
            html = html.replace('<!-- File -->', evidence['name'])
            html = html.replace('<!-- Mimetype -->', 'Directory')
            if 'file_size' in evidence:
                html = html.replace('<!-- Size -->', str(evidence['file_size'][0]) + " Bytes")
            else:
                html = html.replace('<!-- Size -->', "0 Bytes")
            html = html.replace('<!-- Links -->', "\n".join(plugins))
        else:
            html = html.replace('<!-- File -->', evidence['name'])
            html = html.replace('<!-- Mimetype -->', mimetype)
            html = html.replace('<!-- Size -->', str(size) + " Bytes")
            html = html.replace('<!-- Links -->', "\n".join(plugins))

        return html
