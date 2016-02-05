"""
Gets all Log2Timeline entries for the current file
"""

from yapsy.IPlugin import IPlugin
import os

class FaTimeline(IPlugin):

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
        return "Log2Timeline"

    def check(self, curr_file, path_on_disk, mimetype, size):
        """Checks if the file is compatable with this plugin"""

        return 'parser' in curr_file

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def popularity(self):
        """Returns the popularity which is used to order the apps from 1 (low) to 10 (high), default is 5"""
        return 6

    def parent(self):
        """Returns if the plugin accepts other plugins (True) or only files (False)"""
        return False

    def cache(self):
        """Returns if caching is required"""
        return True

    def get(self, curr_file, helper, path_on_disk, mimetype, size, request, children):
        """Returns the result of this plugin to be displayed in a browser"""

        mode = helper.get_request_value(request, 'mode')
        page = int(helper.get_request_value(request, 'page', 1))
        rows = int(helper.get_request_value(request, 'rows', 100))
        sort = helper.get_request_value(request, 'sort')
        order = helper.get_request_value(request, 'order', 'asc')
    
        query_body = {}
        query_body['from'] = rows * (page - 1)
        query_body['size'] = rows
        if sort:
            query_body['sort'] = { sort : order } 
        if curr_file['meta_type'] == 'Directory':
            query_body['query'] = {
                "bool" : {
                    "must": 
                        { 
                            "match_phrase": { "display_name": curr_file['display_name'] }
                        },
                    "must_not":
                        {
                            "term": { "parser": 'efetch' }
                        }
                    }
                }
        else:
            query_body["query"] = {
                "bool" : {
                    "must": 
                        { 
                            "term": { "inode": curr_file['inode'] }
                        },
                    "must_not":
                        {
                            "term": { "parser": 'efetch' }
                        }
                    }
                }

        events = helper.db_util.elasticsearch.search(index='efetch-evidence_' + curr_file['image_id'], doc_type='event', body=query_body)

        #Create Table
        table = '<thead>\n<tr>\n'
        columns = set()
        for item in events['hits']['hits']:
            source = item['_source']
            for key in source:
                columns.add(key)
        for key in columns:
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
        template = open(curr_dir + '/timeline_template.html', 'r')
        html = str(template.read())
        template.close()

        html = html.replace('<!-- Table -->', table)
        html = html.replace('<!-- PID -->', curr_file['pid'])

        return html
