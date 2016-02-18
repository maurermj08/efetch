"""
A blank parent plugin that simply returns an iframe of its child
"""

from yapsy.IPlugin import IPlugin

class FaBlank(IPlugin):

    def __init__(self):
        self._display_name = 'Frame'
        self._popularity = 0
        self._parent = True
        self._cache = False
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
        if request.query_string:
            query_string = "?" + request.query_string
        else:
            query_string = ""

        return '<body style="margin:0px;"><iframe src="/plugins/' + children + query_string + '" style="border: 0px;height: 100%; width: 100%; position: absolute"></iframe></body>'
