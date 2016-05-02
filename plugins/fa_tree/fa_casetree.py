"""
Displays all primary evidence in a case in a tree view
"""

from yapsy.IPlugin import IPlugin
import os
from bottle import route, run, static_file, response, post, request, abort


class FaCasetree(IPlugin):
    DEFAULT_CHILDREN = "/fa_casetree/fa_menu/fa_dirtree/fa_filebrowser/"

    def __init__(self):
        self.display_name = 'Case Tree View'
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

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        if "case" not in request.query and not request.forms.getall('case'):
            abort(400, 'No case specified')

        if "case" in request.query:
            case = request.query['case']
        else:
            case = request.forms.get('case')

        try:
            cases = helper.db_util.read_case(case)
        except:
            abort(404, 'Could not find case ' + case)

        evidence_list = cases['_source']['evidence']
        tree = []
        for item in evidence_list:
            tree.append('<li>' + item)

        child_plugins = ''

        if children:
            child_plugins = children
        else:
            child_plugins = DEFAULT_CHILDREN
            children = DEFAULT_CHILDREN

        if request.query_string:
            query_string = "?" + request.query_string
        else:
            query_string = ""

        curr_dir = os.path.dirname(os.path.realpath(__file__))
        template = open(curr_dir + '/casetree_template.html', 'r')
        html = str(template.read())
        if not evidence_list:
            return "<xmp>Oops! Case contains no evidence! Please Add Evidence.</xmp>"
        if evidence_list[0]:
            html = html.replace('<!-- Home -->', "/plugins/" + children + evidence_list[0] + '/' + query_string)
        html = html.replace('<!-- Tree -->', '\n'.join(tree))
        html = html.replace('<!-- Child -->', "/plugins/" + child_plugins)
        html = html.replace('<!-- Query -->', query_string)
        html = html.replace('<!-- Name -->', 'Evidence')
        template.close()

        return html
