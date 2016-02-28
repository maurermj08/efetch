"""
Gets all Log2Timeline entries for the current file
"""

from yapsy.IPlugin import IPlugin
from urllib import urlencode
import ast
import os
import logging

class FaTimeline(IPlugin):

    def __init__(self):
        self._display_name = 'Log2Timeline'
        self._popularity = 6
        self._parent = True
        self._cache = False
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
        
    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""

        raw_filter = helper.get_request_value(request, 'filter', '{}')
        mode = helper.get_request_value(request, 'mode')
        page = int(helper.get_request_value(request, 'page', 1))
        rows = int(helper.get_request_value(request, 'rows', 100))
        sort = helper.get_request_value(request, 'sort')
        order = helper.get_request_value(request, 'order', 'asc')

        if request.query_string:
            query_string = "?" + request.query_string
        else:
            query_string = ""

        query_body = {}
        query_body['from'] = rows * (page - 1)
        query_body['size'] = rows

        #Gets the filter
        try:
            filter_query = ast.literal_eval(raw_filter)
        except:
            logging.warn('Bad filter %s', raw_filter)
            filter_query = {}

        if sort:
            query_body['sort'] = { sort : order } 
        if evidence['meta_type'] == 'Directory':
            query_bool = { 'must_not' : {"term": { "parser": 'efetch' }} }
            if 'display_name' in evidence:
                query_bool['must'] = { "match_phrase": { "display_name": evidence['display_name']}}
            elif evidence['dir'] != '/':
                query_bool['must'] = { "match_phrase": { "display_name": (evidence['pid'] + '/').split('/', 1)[1].replace('/',':')}}
        else:
            query_bool = {
                    "must": 
                        { 
                            "term": { "inode": evidence['inode'] }
                        },
                    "must_not":
                        {
                            "term": { "parser": 'efetch' }
                        }
                }

        if filter_query:
            if 'must' in query_bool:
                filter_query = helper.db_util.append_dict(filter_query, 'must', query_bool['must'])
            if 'must_not' in query_bool:
                filter_query = helper.db_util.append_dict(filter_query, 'must_not', query_bool['must_not'])
            query_body['query'] = { 'bool' : filter_query }
        else:   
            query_body['query'] = { 'bool' : query_bool }

        events = helper.db_util.elasticsearch.search(index='efetch-evidence_' + evidence['image_id'], doc_type='event', body=query_body)

        #Create Table
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
        if raw_filter:
            html = html.replace('<!-- Filter -->', '&' + urlencode({'filter': raw_filter}))
        else:
            html = html.replace('<!-- Filter -->', '')
        if child_plugins:
            html = html.replace('<!-- Home -->', "/plugins/" + children + query_string)
            html = html.replace('<!-- Child -->', helper.plugin_manager.getPluginByName(str(children.split('/', 1)[0]).lower()).plugin_object._display_name)

        return html
