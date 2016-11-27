"""
Runs a single plugin against multiple path specs from an Elasticsearch query
"""

import os
from yapsy.IPlugin import IPlugin


class FaAction(IPlugin):

    def __init__(self):
        self.display_name = 'Action'
        self.popularity = 0
        self.cache = False
        self.fast = True
        self.action = False
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
        """Returns the result of this plugin to be displayed in a browser"""
        index = helper.get_request_value(request, 'index', False, raise_key_error=True)
        theme = helper.get_theme(request)
        query_string = helper.get_query_string(request)
        curr_dir = os.path.dirname(os.path.realpath(__file__))

        template = open(curr_dir + '/action_template.html', 'r')
        html = str(template.read())
        template.close()

        plugins_list = []
        for plugin in helper.plugin_manager.get_all_plugins():
            # TODO should we use this check: if hasattr(plugin, 'action') and plugin.action:
            plugin_object = helper.plugin_manager.get_plugin_by_name(plugin)
            display_name = plugin_object.display_name
            if getattr(plugin_object, 'action', False):
                plugins_list.append('<!-- For shorting ' + display_name + '--><option value="' + plugin + '">' +
                                    display_name + '</option>')
        plugins_list.sort()

        fields_list = []
        mapping = helper.db_util.get_mappings(index)
        for key in mapping[index]['mappings']['plaso_event']['properties']:
            fields_list.append('<option value="' + key + '">' + key + '</option>')
        fields_list.sort()

        html = html.replace('<!-- Theme -->', theme)
        html = html.replace('<!-- Index -->', index)
        html = html.replace('<!-- Plugins -->', '        \n'.join(plugins_list))
        html = html.replace('<!-- Fields -->', '        \n'.join(fields_list))
        html = html.replace('<!-- Query -->', query_string)

        return html