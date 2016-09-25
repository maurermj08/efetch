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
        self.resource_dir = self.curr_dir + os.path.sep + u'resources' + os.path.sep
        self.icon_dir = self.resource_dir + u'icons' + os.path.sep
        self.output_dir = output_directory
        self.max_file_size = max_file_size
        if not os.path.isdir(self.icon_dir):
            logging.error(u'Could not find icon directory ' + self.icon_dir)

        self.pathspec_helper = PathspecHelper(output_directory, max_file_size)

        # Create plugin manager and begin polling for changes to plugins
        self.plugin_manager = EfetchPluginManager(plugins_file, self.curr_dir)
        self.poll = Poll(self.plugin_manager)
        self.poll.start()

        # Elastic Search DB setup
        if es_url:
            self.db_util = DBUtil()
        else:
            self.db_util = DBUtil(es_url)

    def get_request_value(self, request, variable_name, default=None):
        """Gets the value of a variable in either a GET or POST request"""
        if variable_name in request.query:
            return request.query[variable_name]
        elif request.forms.get(variable_name):
            return request.forms.get(variable_name)
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