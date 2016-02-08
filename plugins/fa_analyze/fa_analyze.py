"""
Basic UI for browsing and analyzing files
"""

from yapsy.IPlugin import IPlugin
import os
import logging

class FaAnalyze(IPlugin):

    def __init__(self):
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def display_name(self):
        """Returns the name displayed in the webview"""
        return "Analyze"

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 0

    def parent(self):
        """Returns if the plugin accepts other plugins (True) or only files (False)"""
        return False

    def cache(self):
        """Returns if caching is required"""
        return True

    def get(self, evidence, helper, path_on_disk, request, children):
        """Provides a web view with all applicable plugins, defaults to most popular"""
        
        #Add Directoy link
        plugins = []
        plugins.append('<a href="/plugins/fa_loader/fa_directory/' + evidence['pid'] + '" target="frame">Directory</a><br>')

        if not evidence['mimetype']:
            mimetype = helper.guess_mimetype(evidence['ext'])
        else:
			mimetype = evidence['mimetype']    
        if 'file_size' not in evidence:
            size = 0
        else:
            size = evidence['file_size'][0]

        #Order Plugins by populatiry from highest to lowest
        for pop in reversed(range(1, 11)):
            for plugin in helper.plugin_manager.getAllPlugins():
                if plugin.plugin_object.popularity() == pop:
                    #Check if plugin applies to curr file
                    if plugin.plugin_object.check(evidence, path_on_disk):
                        logging.debug("Check matched, adding plugin " + plugin.plugin_object.display_name())
                        plugins.append('<a href="/plugins/fa_loader/' + plugin.name + '/' + evidence['pid'] + '" target="frame">' + plugin.plugin_object.display_name() + '</a><br>')
                    else:
                        logging.debug("Check did not match, NOT adding plugin " + plugin.plugin_object.display_name())

        #Modifies HTML page
        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/analyze_template.html', 'r')
        html = str(template.read())
        template.close()
        html = html.replace('<!-- Home -->', "/plugins/fa_loader/fa_directory/" + evidence['pid'])
        
        if evidence['meta_type'] == 'Directory':
            html = html.replace('<!-- File -->', evidence['name'])
            html = html.replace('<!-- Mimetype -->', 'Directory')
            html = html.replace('<!-- Size -->', str(evidence['file_size'][0]) + " Bytes")
            html = html.replace('<!-- Links -->', "\n".join(plugins))
        else:
            html = html.replace('<!-- File -->', evidence['name'])
            html = html.replace('<!-- Mimetype -->', mimetype)
            html = html.replace('<!-- Size -->', str(size) + " Bytes")
            html = html.replace('<!-- Links -->', "\n".join(plugins))
        
        return html


