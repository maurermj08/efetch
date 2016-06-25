# -*- coding: utf-8 -*-
"""An output module that saves data into an ElasticSearch database."""

import logging
import multiprocessing
import os
import sys
import uuid

try:
  from elasticsearch import Elasticsearch
  from elasticsearch import helpers
except ImportError:
  Elasticsearch = None

from plaso.lib import errors
from plaso.lib import timelib
from plaso.output import interface
from plaso.output import manager


def _ProcessEvents(queue, index_name, doc_type, elastic_host, elastic_port, image_id, image_path, output_mediator):
  """Formats all Plaso Events and loads them into Elastic Search"""
  data = []
  size = len(queue)

  while queue:
    event_object = queue.pop(0)
    try:
      data.append(_EventToDict(event_object, image_id, image_path, output_mediator, doc_type, index_name))
    except Exception as e:
      logging.warn('Failed to add event ' + event_object.GetValues()['display_name'])
      logging.warn('Because: ' + e.message)

  elastic_search = Elasticsearch(u'http://{0:s}:{1:d}'.format(elastic_host, elastic_port, index_name, doc_type))
  helpers.bulk(elastic_search, data)
  logging.info('Finished ' + str(size) + ' Events')
  return size


def _EventToDict(event_object, image_id, image_path, output_mediator, doc_type, index):
  """Returns a dict built from an event object.

  Args:
    event_object: the event object (instance of EventObject).
  """
  ret_dict = event_object.GetValues()

  # Perform additional parsing to allow for more data analysis options
  ret_dict['image_id'] = image_id
  root, path = ret_dict['display_name'].split(':/',1)
  path = '/' + path
  root = image_id + '/' + root.replace(':', '/')
  pid = root + path
  name = os.path.basename(path)
  directory = os.path.dirname(pid) + '/'
  ext = os.path.splitext(name)[1][1:] or ""
  ret_dict['pid'] = pid
  ret_dict['name'] = name
  ret_dict['dir'] = directory
  ret_dict['ext'] = ext.lower()
  ret_dict['image_id'] = image_id
  if 'pathspec' in ret_dict:
    del ret_dict['pathspec']

  ret_dict['tag'] = []

  # To not overload the index, remove the regvalue index.
  if 'regvalue' in ret_dict:
    del ret_dict['regvalue']

  # Adding attributes in that are calculated/derived.
  # We want to remove millisecond precision (causes some issues in
  # conversion).
  ret_dict['datetime'] = timelib.Timestamp.CopyToIsoFormat(
    timelib.Timestamp.RoundToSeconds(event_object.timestamp),
    timezone=output_mediator.timezone)

  message, _ = output_mediator.GetFormattedMessages(event_object)
  if message is None:
    raise errors.NoFormatterFound(
      u'Unable to find event formatter for: {0:s}.'.format(
        getattr(event_object, u'data_type', u'UNKNOWN')))

  ret_dict['message'] = message

  source_short, source = output_mediator.GetFormattedSources(
    event_object)
  if source is None or source_short is None:
    raise errors.NoFormatterFound(
      u'Unable to find event formatter for: {0:s}.'.format(
        getattr(event_object, u'data_type', u'UNKNOWN')))

  ret_dict['source_short'] = source_short
  ret_dict['source_long'] = source

  hostname = output_mediator.GetHostname(event_object)
  ret_dict['hostname'] = hostname

  username = output_mediator.GetUsername(event_object)
  ret_dict['username'] = username

  return {
        "_index": index,
        "_type": doc_type,
        "_id": ret_dict['uuid'],
        "_source": ret_dict
  }


class ElasticSearchOutputModule(interface.OutputModule):
  """Saves the events into an ElasticSearch database."""
  NAME = u'elastic'
  DESCRIPTION = u'Saves the events into an ElasticSearch database.'

  def __init__(self, output_mediator):
    """Initializes the output module object.

    Args:
      output_mediator: The output mediator object (instance of OutputMediator).
    """
    super(ElasticSearchOutputModule, self).__init__(output_mediator)
    self._counter = 0
    self._max_queue_size = 32000
    self._max_efetch_queue_size = 500
    self._max_processes = max([multiprocessing.cpu_count() - 1, 1])
    self._queue = []
    # Max tasks per child is being used to prevent out of memory error
    self._process_pool = multiprocessing.Pool(processes=self._max_processes, maxtasksperchild=100)
    self._efetch_queue = []
    self._efetch_time_queue = []
    self._data = []
    self._doc_type = None
    self._elastic_db = None
    self._index_name = None
    self._image_id = None
    self._image_id_value = None
    self._case_name = None
    self._image_path = ''
    self._ids = []
    self._elastic_port = None
    self._elastic_host = None


  def Close(self):
    """Disconnects from the elastic search server."""
    if len(self._queue) > 0:
      self._process_pool.apply_async(_ProcessEvents, args=(self._queue, self._index_name,
                                                               self._doc_type,
                                                               self._elastic_host,
                                                               self._elastic_port,
                                                               self._image_id, self._image_path,
                                                               self._output_mediator))
    logging.info('Closing')
    self._process_pool.close()
    self._process_pool.join()
    sys.stdout.write('. [DONE]\n')
    sys.stdout.write('ElasticSearch index name: {0:s}\n'.format(
        self._index_name))
    sys.stdout.flush()

  def SetCaseName(self, case_name):
    """Set the case name for the ElasticSearch database connection.

    Args:
      case_name: the case name, used for the name of the index in the database.
    """
    if not case_name:
      self._case_name = uuid.uuid4().hex
    else:
      self._case_name = case_name.lower()
    self._image_id = self._case_name
    self._index_name = u'case_' + self._case_name

  def SetDocumentType(self, document_type):
    """Set the document type for the ElasticSearch database connection.

    Args:
      document_type: the document type for the ElasticSearch database.
    """
    if document_type:
      self._doc_type = document_type.lower()
    else:
      self._doc_type = u'plaso_event'

  def SetServerInformation(self, elastic_host, elastic_port):
    """Set the ElasticSearch connection.

    Args:
      elastic_host: the hostname or IP address of the ElasticSearch server.
      elastic_port: the port number that the ElasticSearch is listening on.
    """
    self._elastic_host = elastic_host
    self._elastic_port = elastic_port
    self._elastic_db = Elasticsearch(u'http://{0:s}:{1:d}'.format(elastic_host, elastic_port))

  def WriteEventBody(self, event_object):
    """Writes the body of an event object to the output.

    Args:
      event_object: the event object (instance of EventObject).
    """

    self._queue.append(event_object)
    if len(self._queue) >= self._max_queue_size:
      self._process_pool.apply_async(_ProcessEvents, args=(self._queue, self._index_name,
                                                                        self._doc_type,
                                                                        self._elastic_host,
                                                                        self._elastic_port,
                                                                        self._image_id, self._image_path,
                                                                        self._output_mediator))
      self._queue = []
      self._counter = self._counter + self._max_queue_size
      logging.info('Total: %d', self._counter)

  def WriteHeader(self):
    """Writes the header to the output."""
    self._elastic_db.indices.create(index='case', ignore=400)
    self._elastic_db.indices.put_template(name="case", body=evidence_template())

    sys.stdout.write('Inserting data')
    sys.stdout.flush()


def evidence_template():
  """Returns the Elastic Search mapping for Evidence"""
  return {
      'template': 'case*',
      'settings': {
        'number_of_shards': 1
        },
      'mappings':{
        '_default_':{
          '_source':{ 'enabled':True},
          'properties':{
              'root':{'type': 'string', 'index':'not_analyzed'},
              'pid':{'type': 'string', 'index':'not_analyzed'},
              'iid':{'type': 'string', 'index':'not_analyzed'},
              'image_id': {'type': 'string', 'index':'not_analyzed'},
              'image_path':{'type': 'string', 'index':'not_analyzed'},
              'evd_type':{'type': 'string', 'index':'not_analyzed'},
              'name':{'type': 'string', 'index':'not_analyzed'},
              'path':{'type': 'string', 'index':'not_analyzed'},
              'ext':{'type': 'string', 'index':'not_analyzed'},
              'dir':{'type': 'string', 'index':'not_analyzed'},
              'meta_type':{'type': 'string', 'index':'not_analyzed'},
              'inode':{'type': 'string', 'index':'not_analyzed'},
              'file_size':{'type': 'string', 'index':'not_analyzed'},
              'uid':{'type': 'string', 'index':'not_analyzed'},
              'gid':{'type': 'string', 'index':'not_analyzed'},
              'driver':{'type': 'string', 'index':'not_analyzed'},
              'source_short':{'type': 'string', 'index':'not_analyzed'},
              'source_long': {'type': 'string', 'index': 'not_analyzed'},
              'datetime':{'type': 'date', 'format': 'date_optional_time','index': 'not_analyzed'}
              }
        }
      }
  }

manager.OutputManager.RegisterOutput(
    ElasticSearchOutputModule, disabled=Elasticsearch is None)
