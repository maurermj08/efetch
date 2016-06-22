"""
Gets all Log2Timeline entries for the current file
"""

from yapsy.IPlugin import IPlugin
from urllib import urlencode
import os
import logging
import pprint

class FaTimeline(IPlugin):
    def __init__(self):
        self.display_name = 'Log2Timeline'
        self.popularity = 0 # TODO FIX IN ANALYZE
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
        """Checks if the file is compatible with this plugin"""
        return 'parser' in evidence

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children, logs=True, files=False, directories=False,
            sub_directories=True, evidence_item_plugin='fa_timeline', title='Log2timeline',
            prefix = ['name', 'datetime', 'source_short', 'message', 'star'],
            width = [40, 30, 18, 140, 20]):
        """Returns the result of this plugin to be displayed in a browser"""

        # This value is the UUID to the event or file
        uuid = helper.get_request_value(request, 'uuid', False)
        method = helper.get_request_value(request, 'method')
        if method == 'details':
            return self.get_details(evidence, helper, uuid)

        raw_filter = helper.get_request_value(request, 'filter', '{}')
        mode = helper.get_request_value(request, 'mode')
        page = int(helper.get_request_value(request, 'page', 1))
        rows = int(helper.get_request_value(request, 'rows', 100))
        sort = helper.get_request_value(request, 'sort')
        order = helper.get_request_value(request, 'order', 'asc')
        query_string = helper.get_query_string(request)
        must = []
        must_not = []

        #Only show specified evidence logs, directories, files
        if not files and not directories:
            must_not.append({'term': {'parser': 'efetch'}})
        elif not logs:
            must.append({'term': {'parser': 'efetch'}})
            if not files:
                must.append({'term': {'meta_type':'Directory'}})
            if not directories:
                must.append({'term': {'meta_type':'File'}})

        query_filters = helper.get_filters(request, must, must_not)
        print('FILTERS: ' + str(query_filters))

        query_body = query_filters

        query_body['from'] = rows * (page - 1)
        query_body['size'] = rows
        if sort:
            query_body['sort'] = {sort: order}
        print('HERETIMELINE: ' + str(query_body))
        pprint.PrettyPrinter(indent=4).pprint(query_body)
        events = helper.db_util.elasticsearch.search(index='efetch_evidence_' + evidence['image_id'], doc_type='plaso_event',
                                                     body=query_body)
        # Create Table
        table = '<thead>\n<tr>\n'
        table += '    <th formatter="formatThumbnail" field="Thumbnail" sortable="false" width="12">Thumbnail</th>\n'
        table += '    <th formatter="formatLinkUrl" field="Link" sortable="false" width="10">Analyze</th>\n'

        width_copy = width[:]

        for key in prefix:
            if not width_copy:
                th_html = 'style="display:none;"'
            elif width_copy[0] == 0:
                th_html = 'style="display:none;"'
                width_copy.pop(0)
            else:
                th_html = 'width="' + str(width_copy.pop(0)) + '"'

            table += '    <th field="' + key + '" sortable="true" ' + th_html \
                     + '>' + key + '</th>\n'

        table += '</tr>\n</thead>\n'

        prefix_copy = prefix[:]

        if 'pid' not in prefix_copy:
            prefix_copy.append('pid')
        if 'uuid' not in prefix_copy:
            prefix_copy.append('uuid')

        if mode == 'events':
            event_dict = {}
            event_dict['total'] = events['hits']['total']
            rows = []
            for item in events['hits']['hits']:
                event_row = {}
                source = item['_source']
                for key in prefix_copy:
                    if key == 'star':
                        if 'star' not in source or not source['star']:
                            event_row[key] = """
                                        <form target='_blank' onsubmit='return toggleStar("""  + '"' + source['pid'] + '", "' + source['uuid'] + '"' + """)'>
                                            <input id='""" + source['uuid'] + """' type='image' src='/resources/images/notbookmarked.png'>
                                        </form>
                                    """
                        else:
                            event_row[key] = """
                                        <form target='_blank' onsubmit='return toggleStar(""" + '"' + source['pid'] + '", "' + source['uuid'] + '"' + """)'>
                                            <input id='""" + source['uuid'] + """' type='image' src='/resources/images/bookmarked.png'>
                                        </form>
                                    """
                    elif key in source:
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
        else:
            child_plugins = None

        if child_plugins:
            template = open(curr_dir + '/split_timeline_template.html', 'r')
        else:
            template = open(curr_dir + '/timeline_template.html', 'r')

        html = str(template.read())
        template.close()

        html = html.replace('<!-- Table -->', table)
        html = html.replace('<!-- Query -->', query_string)

        if child_plugins:
            html = html.replace('<!-- Home -->', "/plugins/" + children + query_string)
            html = html.replace('<!-- Child -->', helper.plugin_manager.getPluginByName(
                str(children.split('/', 1)[0]).lower()).plugin_object.display_name)
            html = html.replace('<!-- Children -->', helper.get_children(evidence['image_id'], children))
        else:
            html = html.replace('<!-- Children -->', self._default_plugin)

        return html

    def get_details(self, evidence, helper, uuid):
        table = [ '<table id="t01" class="display">' ]
        event = helper.db_util.elasticsearch.get(index='efetch_evidence_' + evidence['image_id'], doc_type='plaso_event',
                                                 id=uuid)
        try:
            for key in event['_source']:
                try:
                    table.append('<tr>')
                    table.append('<td>' + str(key) + '</td><td>' + str(event['_source'][key]) + '</td>')
                    table.append('</tr>')
                except:
                    logging.warn('Failed to display row "' + str(key) + '" for uuid ' + str(uuid))
        except:
            logging.warn('Failed to get details for event or evidence with uuid "' + str(uuid) + '"')
            return '<h2> Failed to find details about evidence </h2>'

        table.append('</table>')
        return '\n'.join(table)
