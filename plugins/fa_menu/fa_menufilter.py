"""
A menu panel with filtering options
"""

import json
import logging
import os
import uuid
from bottle import abort
from yapsy.IPlugin import IPlugin


class FaMenuFilter(IPlugin):

    def __init__(self):
        self.display_name = 'Menu Filter'
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
            evidence_item_plugin='fa_menufilter', title='Filter'):
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
        elif method == 'get_type_html':
            return self.get_type_html(helper, helper.get_request_value(request, 'type', {}))

        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/menu_filter_template.html', 'r')
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

        all_filters[str(uuid.uuid4())] = {'value': value, query_type: key, 'type': filter_type}

        return all_filters

    def remove_filter(self, filters, uid):
        """Removes a filter from the dictionary of filters"""
        if not (filters and uid):
            abort(code=400, text='Remove filter requires the UID of the filter')

        all_filters = json.loads(filters)

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

    def get_type_html(self, helper, type):
        if type == 'star':
            return { 'field' : 'star_field' }
        if type in [ 'mtime', 'atime', 'ctime', 'crtime' ]:
            return { 'field' : 'date_field' }
        else:
            return { 'field' : 'searchbox_field' }

    def get_panel_content(self, filters, title, query_type):
        all_filters = json.loads(filters)

        header = """
                <a href="javascript:void(0)" class="easyui-linkbutton" onclick="$('#dg').datagrid('reload');$('#add_evidence_window').window('open')" data-options="plain:true,iconCls:'icon-add'">Evidence</a>
                <a href="javascript:void(0)" class="easyui-linkbutton" onclick="$('#dg_remove').datagrid('reload');$('#remove_evidence_window').window('open')" data-options="plain:true,iconCls:'icon-remove'">Evidence</a>
                <b style="color: darkblue;padding-right: 1em;padding-left: 1em;">|</b>
                <select class="easyui-combobox" name="search_type" id="search_type" style="width:75px;">
                    <option value="filter">Filter</option>
                    <option value="wildcard">Search</option>
                    <option value="regexp">Regex</option>
                </select>
                <select class="easyui-combobox" name="filter_type" id="filter_type" style="width:120px;" data-options="onSelect: function(rec){ filter_type_combobox_change(rec); }">
                    <option value="ext">ext</option>
                    <option value="path">path</option>
                    <option value="name">name</option>
                    <option value="dir">dir</option>
                    <option value="mtime">mtime</option>
                    <option value="atime">atime</option>
                    <option value="ctime">ctime</option>
                    <option value="crtime">crtime</option>
                    <option value="sha256_hash">sha256_hash</option>
                    <option value="meta_type">meta_type</option>
                    <option value="parser">parser</option>
                    <option value="source_short">source_short</option>
                    <option value="star">star</option>
                </select>
                <select class="easyui-combobox" name="filter_type" id="filter_type" style="width:90px;">
                    <option value="must">Must</option>
                    <option value="must_not">Must Not</option>
                    <option value="should">Should</option>
                </select>
                <span id="value_fields">
                    <span id="searchbox_field">
                        <input name="value" class="easyui-textbox" required="true">
                    </span>
                    <span id="star_field" hidden>
                        <input class="easyui-switchbutton" style="width:150px;" data-options="checked:true,onText:'Bookmarked',offText:'Not Bookmarked'">
                    </span>
                    <span id="date_field" hidden>
                        Start:
                        <input class="easyui-datetimebox" style="width:150px;height:24px">
                        End:
                        <input class="easyui-datetimebox" style="width:150px;height:24px">
                    </span>
                </span>
                <a href="javascript:void(0)" class="easyui-linkbutton" onclick="$('#dg_remove').datagrid('reload');$('#remove_evidence_window').window('open')" data-options="plain:true,iconCls:'icon-search'">Apply</a>
                """
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