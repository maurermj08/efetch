"""
Converts office documents to PDF and displays them
"""

from yapsy.IPlugin import IPlugin
from bottle import static_file
import os


class FaOffice(IPlugin):
    def __init__(self):
        self.display_name = 'Adv. Preview'
        self.popularity = 8
        self.parent = False
        self.cache = True
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        allowed = ['application/mspowerpoint', 'application/vnd.ms-powerpoint', 'application/msword',
                   'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/x-latex',
                   'application/application/vnd.oasis.opendocument.text',
                   'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                   'application/vnd.openxmlformats-officedocument.presentationml.slide',
                   'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
                   'application/vnd.openxmlformats-officedocument.presentationml.template',
                   'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                   'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
                   'application/vnd.openxmlformats-officedocument.wordprocessingml.template', 'application/vnd.palm',
                   'application/rtf', 'application/vnd.sun.xml.writer.template', 'application/vnd.sun.xml.writer',
                   'application/vnd.ms-works', 'application/vnd.oasis.opendocument.graphics',
                   'application/vnd.oasis.opendocument.presentation',
                   'application/vnd.oasis.opendocument.presentation-template', 'application/vnd.sun.xml.impress',
                   'application/vnd.ms-excel', 'text/rtf']
        extensions = ['docx', 'docm', 'dotx', 'dotm', 'xlsx', 'xlsm', 'xltx', 'xltm', 'pptx', 'pptm', 'potx', 'potm',
                      'ppsx', 'ppsm', 'sldx', 'sldm']

        return (evidence['meta_type'] == 'File' and str(evidence['mimetype']).lower() in allowed) or \
               (evidence['meta_type'] == 'File' and str(evidence['extension']).lower() in extensions)

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return mimetype

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        newname = os.path.splitext(path_on_disk)[0] + ".pdf"
        if not os.path.isfile(newname):
            os.system("unoconv -f pdf -o '" + newname + "' '" + path_on_disk + "'")
        return static_file(os.path.basename(newname), root=os.path.dirname(newname))
