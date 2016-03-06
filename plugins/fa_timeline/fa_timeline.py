"""
Gets all Log2Timeline entries for the current file
"""

from yapsy.IPlugin import IPlugin
from urllib import urlencode
import os
import logging


class FaTimeline(IPlugin):
    def __init__(self):
        self.display_name = 'Log2Timeline'
        self.popularity = 6
        self.parent = True
        self.cache = False
        self._default_plugin = 'fa_analyze/'
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        return 'parser' in evidence

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children, logs=True, files=False, directories=False,
            sub_directories=True, evidence_item_plugin='fa_timeline'):
        """Returns the result of this plugin to be displayed in a browser"""
        raw_filter = helper.get_request_value(request, 'filter', '{}')
        filter_query = helper.get_filter(request)
        mode = helper.get_request_value(request, 'mode')
        page = int(helper.get_request_value(request, 'page', 1))
        rows = int(helper.get_request_value(request, 'rows', 100))
        sort = helper.get_request_value(request, 'sort')
        order = helper.get_request_value(request, 'order', 'asc')
        query_string = helper.get_query_string(request)

        query_body = {}
        query_body['from'] = rows * (page - 1)
        query_body['size'] = rows

        query_bool = {}

        #Only show evidence with the same image_id
        query_bool = helper.db_util.append_dict(query_bool, 'must', {'term': {'image_id': evidence['image_id']}})

        #Only show specified evidence logs, directories, files
        if not files and not directories:
            query_bool = helper.db_util.append_dict(query_bool, 'must_not', {'term': {'parser': 'efetch'}})
        elif not logs:
            query_bool = helper.db_util.append_dict(query_bool, 'must', {'term': {'parser': 'efetch'}})
            if not files:
                query_bool = helper.db_util.append_dict(query_bool, 'must', {'term': {'meta_type':'Directory'}})
            if not directories:
                query_bool = helper.db_util.append_dict(query_bool, 'must', {'term': {'meta_type':'File'}})

        #If sort, sort the evidence using the given order
        if sort:
            query_body['sort'] = {sort: order}

        #If evidencei is a directory show evidence in that directory
        if evidence['meta_type'] == 'Directory' and not sub_directories:
            query_bool = helper.db_util.append_dict(query_bool, 'must', {"term": {"dir": evidence['pid'] + '/'}})
        elif evidence['meta_type'] == 'Directory':
            query_bool = helper.db_util.append_dict(query_bool, 'must', {"prefix": {"dir": evidence['pid'] + '/'}})
        else:
            query_bool = helper.db_util.append_dict(query_bool, 'must', {"term": {"inode": evidence['inode']}})

        if filter_query:
            #TODO create a helper with a proper join
            if 'must' in query_bool:
                filter_query = helper.db_util.append_dict(filter_query, 'must', query_bool['must'])
            if 'must_not' in query_bool:
                filter_query = helper.db_util.append_dict(filter_query, 'must_not', query_bool['must_not'])
            query_body['query'] = {'bool': filter_query}
        else:
            query_body['query'] = {'bool': query_bool}

        events = helper.db_util.elasticsearch.search(index='efetch-evidence_' + evidence['image_id'], doc_type='event',
                                                     body=query_body)
        # Create Table
        table = '<thead>\n<tr>\n'
        columns = set()
        table += '    <th formatter="formatThumbnail" field="Thumbnail" sortable="false">Thumbnail</th>\n'
        table += '    <th formatter="formatLinkUrl" field="Link" sortable="false">Analyze</th>\n'
        order = ['datetime', 'parser', 'message']

        for item in events['hits']['hits']:
            source = item['_source']
            for key in source:
                columns.add(key)
        for key in order:
            table += '    <th field="' + key + '" sortable="true">' + key + '</th>\n'
        for key in columns:
            if key not in order:
                table += '    <th field="' + key + '" sortable="true">' + key + '</th>\n'
        table += '</tr>\n</thead>\n'

        if mode == 'events':
            event_dict = {}
            event_dict['total'] = events['hits']['total']
            rows = []
            for item in events['hits']['hits']:
                event_row = {}
                source = item['_source']
                for key in columns:
                    if key in source:
                        try:
                            event_row[key] = str(source[key])
                        except:
                            event_row[key] = source[key]
                    else:
                        event_row[key] = ''
                rows.append(event_row)
            event_dict['rows'] = rows
            return event_dict

        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))

        if evidence['image_id'] in children:
            child_plugins = str(children).split(evidence['image_id'])[0]

        if child_plugins:
            template = open(curr_dir + '/split_timeline_template.html', 'r')
        else:
            template = open(curr_dir + '/timeline_template.html', 'r')

        html = str(template.read())
        template.close()

        html = html.replace('<!-- Table -->', table)
        html = html.replace('<!-- PID -->', evidence['pid'])
        html = html.replace('<!-- Plugin -->', evidence_item_plugin)
        if raw_filter:
            html = html.replace('<!-- Filter -->', '&' + urlencode({'filter': raw_filter}))
        else:
            html = html.replace('<!-- Filter -->', '')
        if child_plugins:
            html = html.replace('<!-- Home -->', "/plugins/" + children + query_string)
            html = html.replace('<!-- Plugin -->', child_plugins)
            html = html.replace('<!-- Child -->', helper.plugin_manager.getPluginByName(
                str(children.split('/', 1)[0]).lower()).plugin_object.display_name)

        return html
