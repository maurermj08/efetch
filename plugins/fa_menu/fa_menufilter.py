"""
A menu panel with filtering options
"""

import json
import logging
import os
import uuid
from datetime import datetime
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
        method = helper.get_request_value(request, 'method', False)

        if method == 'get_panel_content':
            return self.get_panel_content(helper.get_request_value(request, 'filters', {}), title, query_type)
        elif method == 'add_filter':
            return self.add_filter(helper.get_request_value(request, 'filters', {}),
                                   helper.get_request_value(request, 'search', False),
                                   helper.get_request_value(request, 'key', False),
                                   helper.get_request_value(request, 'operation', False),
                                   helper.get_request_value(request, 'searchbox', False),
                                   helper.get_request_value(request, 'star', False),
                                   helper.get_request_value(request, 'start_datetime', False),
                                   helper.get_request_value(request, 'end_datetime', False))
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
        # TODO Check if case in query, if not disable evidence buttons
        html = html.replace('<!-- Case -->', request.query['case'])

        return html

    def add_filter(self, filters, search, key, operation, searchbox, star, start_datetime,
                   end_datetime):
        """Adds a filter to the dictionary of filters"""
        if not (search and key and operation):
            logging.warn('Failed to add filter, requires a filter type, search type, and operation type')
            abort(code=400, text='Add filter requires a filter type, search type, and operation type')

        all_filters = json.loads(filters)

        if key == 'star':
            if star and operation == 'must_not':
                operation = 'must'
                star = 'true'
            if star.lower() == 'false' and operation == 'must':
                operation = 'must_not'
                star = 'true'
            all_filters[str(uuid.uuid4())] = {'value': star,
                                              'key' : key,
                                              'search': search,
                                              'operation': operation}
        elif (key == 'mtime' or key == 'atime' or key == 'ctime' or
            key == 'crtime' or key =='datetime'):
            if start_datetime:
                all_filters[str(uuid.uuid4())] = {'value': { 'gte':
                                                  datetime.strptime(start_datetime, '%m/%d/%Y %H:%M:%S').isoformat()},
                                                  'key': key,
                                                  'search': 'range',
                                                  'operation': operation,
                                                  'pretty_value': 'after ' + datetime.strptime(start_datetime, '%m/%d/%Y %H:%M:%S').isoformat()}
            if end_datetime:
                all_filters[str(uuid.uuid4())] = {'value': { 'lte':
                                                  datetime.strptime(end_datetime, '%m/%d/%Y %H:%M:%S').isoformat()},
                                                  'key': key,
                                                  'search': 'range',
                                                  'operation': operation,
                                                  'pretty_value': 'before ' + datetime.strptime(end_datetime, '%m/%d/%Y %H:%M:%S').isoformat()}

        else:
            all_filters[str(uuid.uuid4())] = {'value': searchbox,
                                              'key': key,
                                              'search': search,
                                              'operation': operation}

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

        for uid in all_filters:
            query_filter = helper.db_util.append_dict(query_filter, all_filters[uid]['operation'],
                                                      {all_filters[uid]['search']: {all_filters[uid]['key']: all_filters[uid]['value']}})
        return query_filter

    def get_type_html(self, helper, type):
        if type == 'star':
            return { 'field' : 'star_field' }
        if type in [ 'mtime', 'atime', 'ctime', 'crtime', 'datetime' ]:
            return { 'field' : 'date_field' }
        else:
            return { 'field' : 'searchbox_field' }

    def get_panel_content(self, filters, title, query_type):
        all_filters = json.loads(filters)

        header = """
                <a href="javascript:void(0)" class="easyui-linkbutton" onclick="$('#dg').datagrid('reload');$('#add_evidence_window').window('open')" data-options="plain:true,iconCls:'icon-add'">Evidence</a>
                <a href="javascript:void(0)" class="easyui-linkbutton" onclick="$('#dg_remove').datagrid('reload');$('#remove_evidence_window').window('open')" data-options="plain:true,iconCls:'icon-remove'">Evidence</a>
                <b style="color: darkblue;padding-right: 1em;padding-left: 1em;">|</b>
                <select class="easyui-combobox" name="search" id="search" style="width:75px;">
                    <option value="term">Filter</option>
                    <option value="wildcard">Search</option>
                    <option value="regexp">Regex</option>
                </select>
                <select class="easyui-combobox" name="key" id="key" style="width:120px;" data-options="onSelect: function(rec){ key_combobox_change(rec); }">
                    <option value="ext">ext</option>
                    <option value="path">path</option>
                    <option value="name">name</option>
                    <option value="dir">dir</option>
                    <option value="datetime">datetime</option>
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
                <select class="easyui-combobox" name="operation" id="operation" style="width:90px;">
                    <option value="must">Must</option>
                    <option value="must_not">Must Not</option>
                    <option value="should">Should</option>
                </select>
                <span id="value_fields">
                    <span id="searchbox_field">
                        <input id="searchbox" class="easyui-textbox">
                    </span>
                    <span id="star_field" hidden>
                        <input id="star" class="easyui-switchbutton" style="width:150px;" data-options="checked:true,onText:'Bookmarked',offText:'Not Bookmarked'">
                    </span>
                    <span id="date_field" hidden>
                        Start:
                        <input id="start_datetime" class="easyui-datetimebox" style="width:150px;height:24px">
                        End:
                        <input id="end_datetime" class="easyui-datetimebox" style="width:150px;height:24px">
                    </span>
                </span>
                <a href="javascript:void(0)" class="easyui-linkbutton" onclick="addFilter();" data-options="plain:true,iconCls:'icon-search'">Apply</a>
                """
        body = []

        for uid in all_filters:
            if 'pretty_value' in all_filters[uid]:
                formatted_value = all_filters[uid]['pretty_value']
            else:
                formatted_value = '"' + str(all_filters[uid]['value']) + '"'

            title = all_filters[uid]['key'] + ' ' + all_filters[uid]['operation'].replace('_', ' ') + ' be ' + \
                        formatted_value
            body.append(
                """<div class="easyui-menubutton" data-options="menu:'#""" + uid + """',iconCls:'icon-ok'">""" + title + """</div>""")
            body.append("""<div id=""" + '"' + uid + '"' + """ style="width:100px;">""")
            body.append(
                """<div data-options="iconCls:'icon-cancel'" onclick="javascript:removeFilter('""" + uid + """')">Remove</div>""")
            body.append("""</div>""")

        return header + '\n'.join(body)