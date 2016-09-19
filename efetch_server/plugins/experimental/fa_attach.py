"""
Uploads a Base64 attachment of the evidence item to Elasticsearch
"""

from yapsy.IPlugin import IPlugin
import base64
import re


class FaAttach(IPlugin):

    # TODO Write a script to parse:
    # TODO http://grepcode.com/file/repo1.maven.org/maven2/org.apache.tika/tika-core/0.6/org/apache/tika/mime/tika-mimetypes.xml
    tika_supported = ['application/mspowerpoint', 'application/vnd.ms-powerpoint', 'application/msword',
                           'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                           'application/x-latex',
                           'application/application/vnd.oasis.opendocument.text',
                           'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                           'application/vnd.openxmlformats-officedocument.presentationml.slide',
                           'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
                           'application/vnd.openxmlformats-officedocument.presentationml.template',
                           'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
                           'application/vnd.openxmlformats-officedocument.wordprocessingml.template',
                           'application/vnd.palm',
                           'application/rtf', 'application/vnd.sun.xml.writer.template',
                           'application/vnd.sun.xml.writer',
                           'application/vnd.ms-works', 'application/vnd.oasis.opendocument.graphics',
                           'application/vnd.oasis.opendocument.presentation',
                           'application/vnd.oasis.opendocument.presentation-template',
                           'application/vnd.sun.xml.impress',
                           'application/vnd.ms-excel', 'text/rtf', 'image/bmp', 'image/x-ms-bmp', 'image/cgm',
                           'image/gif', 'image/jpeg', 'image/png', 'image/x-niff', 'image/svg+xml', 'image/tiff',
                           'image/x-icon', 'image/x-portable-bitmap',
                           'image/x-portable-anymap', 'image/x-portable-graymaP', 'image/x-portable-anymap"',
                           'image/x-portable-pixmap', 'image/x-portable-anymap',
                           'text/html', 'text/plain', 'text/troff', 'text/x-diff',
                           'video/quicktime', 'video/x-flv', 'video/x-jng', 'video/x-mng',
                           'video/x-msvideo', 'video/avi', 'video/msvideo', 'video/x-sgi-movie',
                           'application/pdf', 'application/x-pdf', 'application/postscript',
                           'application/x-bibtex-text-file', 'application/x-compress', 'application/x-gzip',
                           'application/xml', 'application/zip', 'audio/basic', 'audio/mpeg', 'audio/x-wav']

    def __init__(self):
        self.display_name = 'Base64 Attach'
        self.popularity = 3
        self.cache = False
        self.fast = False

        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        return evidence['meta_type'] == 'File'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    # TODO - Major bug, repeats self
    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        return '<xmp>' + str(helper.action_get(evidence,
                                               request, self.display_name, self.base64_evidence, 'attachment')) + \
               '</xmp>'

    @staticmethod
    def base64_evidence(evidence, helper):
        """Returns a Base64 encoded string of the provided evidence"""
        #try
        if evidence['mimetype'] in FaAttach.tika_supported:
            return {
                '_indexed_chars': -1,
                '_content': base64.b64encode(helper.pathspec_helper.read_file(evidence['pathspec']))
            }
        else:
            return {
                '_indexed_chars': -1,
                '_content': base64.b64encode("\n".join(helper.pathspec_helper.get_file_strings(evidence['pathspec'])))
            }
        # except:
        #     logging.warn('Failed to attach the file "' + evidence['file_cache_path'] + '"')