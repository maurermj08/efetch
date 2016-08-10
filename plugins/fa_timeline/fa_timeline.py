"""
Gets all Log2Timeline entries for the current file
"""

from yapsy.IPlugin import IPlugin
import os
import logging
from bottle import abort

class FaTimeline(IPlugin):
    def __init__(self):
        self.display_name = 'Log2Timeline'
        self.popularity = 5
        self.cache = False
        self._default_plugin = 'fa_analyze/'
        self.fast = True
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

    def get(self, evidence, helper, path_on_disk, request, logs=True, files=False, directories=False,
            sub_directories=True, evidence_item_plugin='fa_timeline', title='Log2timeline',
            prefix = ['name', 'datetime', 'source_short', 'message', 'star'],
            width = [40, 30, 18, 140, 20]):
        """Returns the result of this plugin to be displayed in a browser"""

        index = helper.get_request_value(request, 'index', False)
        if not index:
            abort(400, 'Timeline plugin requires an index, but none found')

        # This value is the UUID to the event or file
        uuid = helper.get_request_value(request, 'id', False)
        method = helper.get_request_value(request, 'method')
        if method == 'details':
            return self.get_details(index, helper, uuid)

        theme = helper.get_theme(request)
        mode = helper.get_request_value(request, 'mode')
        page = int(helper.get_request_value(request, 'page', 1))
        rows = int(helper.get_request_value(request, 'rows', 100))
        sort = helper.get_request_value(request, 'sort')
        order = helper.get_request_value(request, 'order', 'asc')
        query_string = helper.get_query_string(request)
        must = []
        must_not = []

        pathspec = helper.get_request_value(request, 'pathspec', False)

        if pathspec:
            must.append({ 'term': { 'pathspec.raw': pathspec}})

        query_filters = helper.get_filters(request, must, must_not)
        query_body = query_filters
        query_body['from'] = rows * (page - 1)
        query_body['size'] = rows
        if sort:
            query_body['sort'] = {sort: order}

        events = helper.db_util.elasticsearch.search(index=index, doc_type='plaso_event',
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

        if 'pathspec' not in prefix_copy:
            prefix_copy.append('pathspec')
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
                                        <form target='_blank' onsubmit='return toggleStar("""  + '"' + index + '", "' + source['uuid'] + '"' + """)'>
                                            <input id='""" + item['_id'] + """' type='image' src='/resources/images/notbookmarked.png'>
                                        </form>
                                    """
                        else:
                            event_row[key] = """
                                        <form target='_blank' onsubmit='return toggleStar(""" + '"' + index + '", "' + source['uuid'] + '"' + """)'>
                                            <input id='""" + item['_id'] + """' type='image' src='/resources/images/bookmarked.png'>
                                        </form>
                                    """
                    elif key in source:
                        try:
                            event_row[key] = str(source[key])
                        except:
                            event_row[key] = source[key]
                    else:
                        event_row[key] = ''
                event_row['index'] = index
                rows.append(event_row)
            event_dict['rows'] = rows
            return event_dict

        curr_dir = os.path.dirname(os.path.realpath(__file__))

        template = open(curr_dir + '/timeline_template.html', 'r')

        html = str(template.read())
        template.close()

        html = html.replace('<!-- Table -->', table)
        html = html.replace('<!-- Query -->', query_string)
        html = html.replace('<!-- Theme -->', theme)
        html = html.replace('<!-- Index -->', index)
        html = html.replace('<!-- Children -->', self._default_plugin)

        return html

    def get_details(self, index, helper, uuid):
        table = [ '<table id="t01" class="display">' ]
        event = helper.db_util.query_uuid(uuid, index)
        if '_index' in event:
            index = event['_index']

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
