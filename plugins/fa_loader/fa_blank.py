"""
A blank parent plugin that simply returns an iframe of its child
"""

from yapsy.IPlugin import IPlugin


class FaBlank(IPlugin):
    def __init__(self):
        self.display_name = 'Frame'
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
        query_string = helper.get_query_string(request)

        return '<body style="margin:0px;"><iframe src="/plugins/' + children + query_string + '" style="border: 0px;height: 100%; width: 100%; position: absolute"></iframe></body>'
