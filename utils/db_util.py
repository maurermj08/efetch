#!/usr/bin/python
import logging
import time
import pprint
import rison
import traceback
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import ConflictError

class DBUtil(object):
    """This class provides helper methods to be used in Efetch and its plugins"""
    elasticsearch = None

    def __init__(self, es_url=None):
        """Creates the Efetch indices in Elasticsearch if they do not exist"""
        if es_url:
            self.elasticsearch = Elasticsearch([es_url])
        else:
            self.elasticsearch = Elasticsearch()

    # Elastic
    def create_index(self, index_name):
        """Create index in Elasticsearch with the provided name, ignoring error if it exists"""
        self.elasticsearch.indices.create(index=index_name, ignore=400)

    def bulk(self, json):
        """Bulk adds json to Elastic Search"""
        helpers.bulk(self.elasticsearch, json)

    def query(self, query, index, size=False):
        """Returns the results of an Elasticsearch query without error checking"""
        if size:
            query['size'] = size
        return self.elasticsearch.search(index=index, body=query)

    def query_id(self, id, index, doc_type='_all'):
        """Returns the result of an Elasticsearch request for the specified ID"""
        if not id:
            logging.warn('No ID provided for query_id')
            return {}
        return self.elasticsearch.get(index=index, id=id, doc_type=doc_type)

    def query_sources(self, query, index, size=False):
        """Returns the source values of an Elasticsearch query without error checking"""
        return self.get_sources(self.query(query, index))

    def update(self, id_value, index, update, doc_type, abort_on_error=True, repeat=1):
        """Updates evidence event in Elastic Search"""
        try:
            self.elasticsearch.update(index=index, doc_type=doc_type, id=id_value, body={'doc': update})
        except ConflictError:
            if repeat > 0:
                logging.info('Failed to update "' + id_value + '" attempting again in 200ms')
                time.sleep(.200)
                self.update(id, index, update, abort_on_error, repeat - 1)
            logging.warn('Failed to update "' + id_value + '" due to conflict error!')

    def get_query(self, a_parameter):
        """Returns the query from _a RISON"""
        try:
            a_parsed = rison.loads(a_parameter)
        except Exception, err:
            logging.error('Failed to parse rison: ' + a_parameter)
            traceback.print_exc()
            return {'query_string': {'analyze_wildcard': True, 'query': '*'}}
        if 'query' in a_parsed:
            return a_parsed['query']
        else:
            return {'query_string': {'analyze_wildcard': True, 'query': '*'}}

    # Kibana
    def get_theme(self, a_parameter):
        """Returns the theme from _a RISON"""
        try:
            a_parsed = rison.loads(a_parameter)
        except Exception, err:
            logging.error('Failed to parse rison: ' + a_parameter)
            traceback.print_exc()
            return {'query_string': {'analyze_wildcard': True, 'query': '*'}}
        if 'options' in a_parsed and 'darkTheme' in a_parsed['options'] and a_parsed['options']['darkTheme']:
            return 'black'
        else:
            return 'default'

    def get_filters(self, a_parameter, g_parameter, must=[], must_not=[]):
        """Returns the query from _a RISON"""
        a_parsed = rison.loads(a_parameter)
        g_parsed = rison.loads(g_parameter)

        if 'time' in g_parsed:
            # pprint.pprint(g_parsed)
            must.append({'range': {'datetime': {
                'gte': g_parsed['time']['from'],
                'lte': g_parsed['time']['to']
            }}})

        # pprint.PrettyPrinter(indent=4).pprint(a_parsed)
        if 'filters' in a_parsed:
            for filter in a_parsed['filters']:
                if not filter['meta']['negate']:
                    must.append({'query': filter['query']})  # , '$state': filter['$state']})
                else:
                    must_not.append({'query': filter['query']})  # , '$state': filter['$state']})

        query = {
            'query': {
                'filtered': {
                    'query': {
                        'query_string': {
                            'query': '*',
                            'analyze_wildcard': True
                        }
                    }
                }
            }
        }

        if 'query' in a_parsed:
            must.append({'query': a_parsed['query']})

        if not must and not must_not:
            return query

        query['query']['filtered']['filter'] = {'bool': {}}

        if must:
            # if len(must) == 1:
            #    must = must[0]
            query['query']['filtered']['filter']['bool']['must'] = must
        if must_not:
            # if len(must_not) == 1:
            #    must_not = must_not[0]
            query['query']['filtered']['filter']['bool']['must_not'] = must_not

        return query

    def get_sources(self, query_result, abort_on_error=False):
        """Gets the _source values out of an Elasticsearch query"""
        if not query_result['hits'] or not query_result['hits']['hits'] \
                or not query_result['hits']['hits'][0]['_source']:
            logging.warn("Could not find any results from query.")
            return []

        return query_result['hits']['hits'][0]['_source']

    def append_dict(self, dictionary, key, value):
        """Appends values to a dictionary in the format Elasticsearch expects"""
        if not dictionary:
            dictionary = {}
        if not key in dictionary:
            dictionary[key] = value
        elif isinstance(dictionary[key], list):
            dictionary[key].append(value)
        else:
            dictionary[key] = [dictionary[key], value]
        
        return dictionary
