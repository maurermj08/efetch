"""
Displays all exts in a tree view
"""

from yapsy.IPlugin import IPlugin
import os
from bottle import route, run, static_file, response, post, request, abort


class FaExttree(IPlugin):
    def __init__(self):
        self.display_name = 'Case Tree View'
        self.popularity = 0
        self.parent = True
        self.cache = False
        self._default_child = '/fa_dirbrowser/fa_analyze/'
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""

        tree = []
        for item in evidence_list:
            tree.append('<li>' + item)

        child_plugins = ''

        if children:
            child_plugins = children
        else:
            child_plugins = self._default_child
            children = self._default_child

        if request.query_string:
            query_string = "?" + request.query_string
        else:
            query_string = ""

        events = helper.db_util.elasticsearch.search(index='efetch_evidence_' + evidence['image_id'], doc_type='event',
                                                     body=ext_query(evidence['pid']))

        # TODO LOOP THROUGH EVENTS

        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/casetree_template.html', 'r')
        html = str(template.read())
        html = html.replace('<!-- Home -->', "/plugins/" + children + evidence['image_id'] + '/' + query_string)
        html = html.replace('<!-- Tree -->', '\n'.join(tree))
        html = html.replace('<!-- Child -->', "/plugins/" + child_plugins)
        html = html.replace('<!-- Query -->', query_string)
        html = html.replace('<!-- Name -->', 'Extensions')
        template.close()

        return html

    # TODO ADD MUST
    def ext_query(pid):
        return {
            "size": 0,
            "query": {
                "term": {
                    'parser': 'efetch',
                    'dir': 'pid' + '/'
                }
            },
            "aggregations": {
                "event": {
                    "terms": {
                        "field": "ext"
                    }
                }
            }
        }
