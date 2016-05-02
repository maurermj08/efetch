"""
A parent plugin that adds a filter to its child plugins
"""

import json
import logging
import os
import uuid
from bottle import abort
from yapsy.IPlugin import IPlugin


class FaFilter(IPlugin):
    def __init__(self):
        self.display_name = 'Filter Bar'
        self.popularity = 0
        self.parent = True
        self.cache = False
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

    def get(self, evidence, helper, path_on_disk, request, children, query_type='term',
            evidence_item_plugin='fa_filter', title='Filter'):
        """Gets the filter bar"""
        method = helper.get_request_value(request, evidence_item_plugin + '_method', False)

        if method == 'get_panel_content':
            return self.get_panel_content(helper.get_request_value(request, 'filters', {}), title, query_type)
        elif method == 'add_filter':
            return self.add_filter(helper.get_request_value(request, 'filters', {}),
                                   helper.get_request_value(request, 'value', False),
                                   helper.get_request_value(request, query_type, False),
                                   helper.get_request_value(request, 'type', False), query_type)
        elif method == 'remove_filter':
            return self.remove_filter(helper.get_request_value(request, 'filters', {}),
                                      helper.get_request_value(request, 'uid', False))
        elif method == 'get_filter':
            return self.get_filter(helper, helper.get_request_value(request, 'filters', {}), query_type)

        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/filter_template.html', 'r')
        html = str(template.read())
        query_string = helper.get_query_string(request)

        raw_filter = helper.get_request_value(request, 'filter', '{}')
        html = html.replace('<!-- Filters -->', raw_filter)
        html = html.replace('<!-- Type -->', query_type)
        html = html.replace('<!-- Plugin -->', evidence_item_plugin)
        html = html.replace('<!-- Home -->', "/plugins/" + children + query_string)

        return html

    def add_filter(self, filters, value, key, filter_type, query_type):
        """Adds a filter to the dictionary of filters"""
        if not (value and key and filter_type):
            logging.warn('Failed to add filter where value=%s, %s=%s, and type=%s', value, query_type, key, filter_type)
            abort(code=400, text='Add filter requires a value, key, and filter type')
        all_filters = json.loads(filters)
        if 'readyState' in all_filters:
            del all_filters['readyState']

        #if key == 'star':
        #    if value.lower() == 'true':
        #        value = True
        #    else:
        #        value = False

        all_filters[str(uuid.uuid4())] = {'value': value, query_type: key, 'type': filter_type}

        return all_filters

    def remove_filter(self, filters, uid):
        """Removes a filter from the dictionary of filters"""
        if not (filters and uid):
            abort(code=400, text='Remove filter requires the UID of the filter')

        all_filters = json.loads(filters)
        # if 'readyState' in all_filters:
        #    del all_filters['readyState']

        if uid not in all_filters:
            abort(code=404, text='Could not find uid in filters')

        del all_filters[uid]

        return all_filters

    def get_filter(self, helper, filters, query_type):
        all_filters = json.loads(filters)

        query_filter = {}

        for key in all_filters:
            query_filter = helper.db_util.append_dict(query_filter, all_filters[key]['type'],
                                                      {query_type: {all_filters[key][query_type]: all_filters[key]['value']}})

        return query_filter

    def get_panel_content(self, filters, title, query_type):
        all_filters = json.loads(filters)

        header = """
            <b style="color: darkblue;padding-right: 1em;padding-left: 1em;">""" + title + """</b>
            <select class="easyui-combobox" name="filter_type" id="filter_type" style="width:100px;">
                <option value="must">Must</option>
                <option value="must_not">Must Not</option>
                <option value="should">Should</option>
            </select>
            <input class="easyui-searchbox" data-options="prompt:'Please Input Value',menu:'#filter_""" + query_type + """',searcher:addFilter" style="width:300px"></input>
            <div id="filter_""" + query_type + """">
                <div data-options=""" + '"' + query_type + """:'path'">path</div>
                <div data-options=""" + '"' + query_type + """:'name'">name</div>
                <div data-options=""" + '"' + query_type + """:'ext'">ext</div>
                <div data-options=""" + '"' + query_type + """:'dir'">dir</div>
                <div data-options=""" + '"' + query_type + """:'sha256_hash'">sha256_hash</div>
                <div data-options=""" + '"' + query_type + """:'meta_type'">meta_type</div>
                <div data-options=""" + '"' + query_type + """:'parser'">parser</div>
                <div data-options=""" + '"' + query_type + """:'source_short'">source_short</div>
                <div data-options=""" + '"' + query_type + """:'source_short'">star</div>
            </div>"""
        body = []

        for key in all_filters:
            title = all_filters[key][query_type] + ' ' + all_filters[key]['type'].replace('_', ' ') + ' be "' + \
                    str(all_filters[key]['value']) + '"'
            body.append(
                """<div class="easyui-menubutton" data-options="menu:'#""" + key + """',iconCls:'icon-ok'">""" + title + """</div>""")
            body.append("""<div id=""" + '"' + key + '"' + """ style="width:100px;">""")
            body.append(
                """<div data-options="iconCls:'icon-cancel'" onclick="javascript:removeFilter('""" + key + """')">Remove</div>""")
            body.append("""</div>""")

        return header + '\n'.join(body)
