# Copyright 2016 Michael J Maurer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging
import os
from db_util import DBUtil
from pathspec_helper import PathspecHelper
from plugin_manager import EfetchPluginManager
from poll import Poll


class EfetchHelper(object):
    """This class provides helper methods to be used in Efetch and its plugins"""


    def __init__(self, curr_directory, output_directory, max_file_size, plugins_file, es_url):
        """Initializes the Efetch Helper"""
        # Setup directory references
        self.curr_dir = curr_directory
        self.resource_dir = self.curr_dir + os.path.sep + u'static' + os.path.sep
        self.icon_dir = self.resource_dir + u'icons' + os.path.sep
        self.output_dir = output_directory
        self.max_file_size = max_file_size
        if not os.path.isdir(self.icon_dir):
            logging.error(u'Could not find icon directory ' + self.icon_dir)

        self.pathspec_helper = PathspecHelper(output_directory, max_file_size)

        # Create plugin manager and begin polling for changes to plugins
        self.plugin_manager = EfetchPluginManager(plugins_file, self.curr_dir)
        #self.poll = Poll(self.plugin_manager)
        #self.poll.start()

        self.standard_office_2007_extensions = ['xlsx', 'docx', 'pptx', 'dotx', 'docm', 'doct', 'xlsm', 'xltx', 'xltm',
                                                 'pptx', 'pptm', 'potx', 'ppam', 'ppsx', 'ppsm', 'sldx', 'sldm']

        # Elastic Search DB setup
        if es_url:
            self.db_util = DBUtil()
        else:
            self.db_util = DBUtil(es_url)

    def get_request_value(self, request, variable_name, default=None, raise_key_error=False):
        """Gets the value of a variable in either a GET or POST request"""
        if variable_name in request.args:
            return request.args[variable_name]
        elif variable_name in request.form:
            return request.form[variable_name]
        elif raise_key_error:
            logging.error('Required variable "' + variable_name + '" missing from request')
            raise KeyError('This request requires variable "' + variable_name + '"')

        return default

    def get_query_string(self, request, default_query=''):
        """Returns the query string of the given request"""
        if request.query_string:
            return "?" + request.query_string
        else:
            return default_query

    def get_query(self, request):
        """Gets the Kibana Query from the request"""
        return self.db_util.get_query(self.get_request_value(request, '_a', '()'))

    def get_theme(self, request):
        """Gets the Kibana Theme from the request"""
        return self.db_util.get_theme(self.get_request_value(request, '_a', '()'))

    def get_filters(self, request, must=[], must_not=[]):
        """Gets the Kibana Filter from the request"""
        return self.db_util.get_filters(self.get_request_value(request, '_a', '()'),
                                        self.get_request_value(request, '_g', '()'),
                                        self.get_request_value(request, 'timefield', 'datetime'),
                                        must, must_not)

    def is_expandable_evidence(self, evidence):
        """Returns True if evidence should be expandable and false if not"""
        # Separated for cleanliness, ordering matters here

        # Partitions and volume shadows are expandable
        if 'type_indicator' in evidence and evidence['type_indicator'] in ['TSK_PARTITION', 'VSHADOW']:
            return True

        # Volumes are expandable
        if 'volume_type' in evidence:
            return True

        # Most Storage types are expandable
        if 'storage_type' in evidence:
            # Not E02-E0N files
            if evidence['extension'].lower().startswith('e0') and evidence['extension'].lower() != 'e01':
                return False
            # All other storage types are expandable
            return True

        # Compression types are expandable
        if 'compression_type' in evidence:
            return True

        # Most archive types are expandable
        if 'archive_type' in evidence:
            # Not files with office 2007 mimetypes
            if evidence['mimetype'].startswith('application/vnd'):
                return False
            # Not files with office 2007 extensions
            if evidence['extension'].lower() in self.standard_office_2007_extensions:
                return False
            # All other archives are expandable
            return True

        # Everything else is not expandable
        return False

    def get_icon(self, evidence, resource=True):
        """Returns either an icon or thumbnail of the provided file"""
        if resource:
            curr_icon_dir = '/static/icons/'
        else:
            curr_icon_dir = self.icon_dir

        if 'volume_type' in evidence or 'storage_type' in evidence or 'compression_type' in evidence \
                or 'archive_type' in evidence:
            if not evidence['mimetype_known']:
                evidence['mimetype'] = self.pathspec_helper.get_mimetype(evidence['pathspec'])
        if self.is_expandable_evidence(evidence):
            return curr_icon_dir + '_evidence.png'

        if not 'meta_type' in evidence:
            return curr_icon_dir + '_blank.png'

        # If it is folder just return the folder icon
        if evidence['meta_type'] == 'Directory' or unicode(evidence['file_name']).strip() == "." or unicode(
                evidence['file_name']).strip() == "..":
            return curr_icon_dir + '_folder.png'
        if evidence['meta_type'] != 'File' and evidence['meta_type'] != 'Device':
            return curr_icon_dir + '_blank.png'

        # If the file is an image create a thumbnail
        if evidence['mimetype'].startswith('image') and resource:
            return '/plugins/thumbnail?' + evidence['url_query']
        elif evidence['mimetype'].startswith('image'):
            self.pathspec_helper.create_thumbnail(evidence)

            if os.path.isfile(evidence['thumbnail_cache_path']):
                return evidence['thumbnail_cache_path']
            else:
                return curr_icon_dir + '_missing.png'

        # TODO if mimetype is known, perform a mimetype to extension lookup instead of using extension
        # If file is not an image return the icon associated with the files extension
        else:
            if not os.path.isfile(self.icon_dir + str(evidence['extension']).lower() + '.png'):
                return curr_icon_dir + '_blank.png'
            else:
                return curr_icon_dir + evidence['extension'].lower() + '.png'

    def action_get(self, evidence, request, display_name, function, term, update_term = False):
        """Runs a function that takes an evidence item, updates the term in elastic, and returns the results"""
        index = self.get_request_value(request, 'index', False)
        value = ''

        # Only needed when using elasticsearch just else just return the OCR
        if index:
            # If using elasticsearch get the first entry
            query = {'_source': [term, evidence['pathspec']],
                     'query': {'term': {'pathspec.raw': evidence['pathspec']}}}

            first_elastic_entry = self.db_util.query_sources(query, index, 1)

            # If this plugin has not been run on this entry run it on all entries
            if term not in first_elastic_entry or update_term:
                # Not masking the exception, should be handled by plugin
                value = function(evidence, self)

                try:
                    update = {term: value}
                    events = self.db_util.scan(query, index)

                    for item in events:
                        logging.debug('Updating elasticsearch item: ' + str(item))
                        self.db_util.update(item['_id'], index, update, doc_type=item['_type'])
                except:
                    logging.warn('Failed to update value in elasticsearch')
            else:
                value = first_elastic_entry[term]
        else:
            value = function(evidence, self)

        return value