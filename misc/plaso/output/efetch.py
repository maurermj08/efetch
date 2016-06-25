# -*- coding: utf-8 -*-
"""An output module that saves data into an ElasticSearch database."""

import copy
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
from dfvfs.serializer.json_serializer import JsonPathSpecSerializer
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


def _ProcessEfetchEvents(queue, efetch_time_queue, index_name, doc_type, elastic_host, elastic_port, image_id,
                         image_path, output_mediator):
  """Formats all Efetch Events and loads them into Elastic Search"""
  data = []
  size = len(queue)

  while queue:
    event_object = queue.pop(0)
    try:
      data.append(_EventToEfetch(event_object, efetch_time_queue.pop(0),
                                 image_id, image_path, output_mediator, doc_type, index_name))
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
  #ret_dict['id'] = ret_dict['uuid']
  ret_dict['pid'] = pid
  ret_dict['name'] = name
  ret_dict['dir'] = directory
  ret_dict['path'] = path
  ret_dict['ext'] = ext.lower()
  ret_dict['image_id'] = image_id
  if 'pathspec' in ret_dict:
    ret_dict['pathspec'] = JsonPathSpecSerializer.WriteSerialized(ret_dict['pathspec'])

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


def _EventToEfetch(event_object, event_times, image_id, image_path, output_mediator, doc_type, index):
  """Returns a dict built from an event object.

  Args:
    event_object: the event object (instance of EventObject).
  """
  ret_dict = event_object.GetValues()

  # Perform additional parsing to allow for more data analysis options
  ret_dict['image_id'] = image_id

  # Don't know how I feel about this split... :/ Meh
  root, path = ret_dict['display_name'].split(':/',1)
  path = '/' + path
  root = image_id + '/' + root.replace(':', '/')
  pid = root + path
  name = os.path.basename(path)
  directory = os.path.dirname(pid) + '/'
  ext = os.path.splitext(name)[1][1:] or ""

  if 'inode' in ret_dict:
    iid = root + '/' + str(ret_dict['inode'])
  else:
    iid = root + '/none'

  ret_dict['root'] = root
  #ret_dict['id'] = uuid.uuid4().hex
  ret_dict['uuid'] = uuid.uuid4().hex
  ret_dict['pid'] = pid
  ret_dict['name'] = name
  ret_dict['dir'] = directory
  ret_dict['path'] = path
  ret_dict['ext'] = ext.lower()
  ret_dict['iid'] = iid
  ret_dict['driver'] = 'fa_dfvfs'
  ret_dict['parser'] = 'efetch'

  if 'pathspec' in ret_dict:
    ret_dict['pathspec'] = JsonPathSpecSerializer.WriteSerialized(ret_dict['pathspec'])

  # TODO Need to research elastic tagging, important for future behavior
  #if 'tag' in ret_dict:
  #  del ret_dict['tag']
  #  tag = getattr(event_object, 'tag', None)
  #  if tag:
  #    tags = tag.tags
  #    ret_dict['tag'] = tags
  #    if getattr(tag, 'comment', ''):
  #      ret_dict['comment'] = tag.comment
  #ret_dict['tag'] = []

  if 'timestamp_desc' in ret_dict:
    del ret_dict['timestamp_desc']

  for time_attribute in ['atime', 'ctime', 'crtime', 'mtime']:
    ret_dict[time_attribute] = timelib.Timestamp.CopyToIsoFormat(
          timelib.Timestamp.RoundToSeconds(event_times[time_attribute]),
          timezone=output_mediator.timezone)

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

class EfetchOutputModule(interface.OutputModule):
  """Saves the events into an ElasticSearch database to be used for Efetch."""
  NAME = u'efetch'
  DESCRIPTION = u'Saves the events into an ElasticSearch database to be used for Efetch.'

  def __init__(self, output_mediator):
    """Initializes the output module object.

    Args:
      output_mediator: The output mediator object (instance of OutputMediator).
    """
    super(EfetchOutputModule, self).__init__(output_mediator)
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
    self._roots = []
    self._efetch_event_queue = {}
    self._image_path = ''
    self._ids = []
    self._elastic_port = None
    self._elastic_host = None
    self._efetch_doc_type = 'efetch_event'

  def _RootToDict(self, root, root_uuid):
    sections = root.split('/')
    dictionary = {}
    dictionary['image_id'] = sections[0]
    dictionary['pid'] = root
    if root in self._ids:
      logging.warn('_ID %s already exists', dictionary['pid'])
      return
    else:
      self._ids.append(root)
    dictionary['dir'] = '/'.join(sections[:-1]) + '/'
    dictionary['path'] = root
    dictionary['iid'] = root + '/'
    # dictionary['id'] = uuid.uuid4().hex
    dictionary['uuid'] = root_uuid
    dictionary['name'] = sections[-1]
    dictionary['image_path'] = self._image_path
    dictionary['size'] = '1'
    dictionary['ext'] = ''
    dictionary['datetime'] = '1601-01-01T00:00:00+00:00'
    dictionary['parser'] = 'efetch'
    dictionary['meta_type'] = 'Directory'
    return dictionary

  def Close(self):
    """Disconnects from the elastic search server."""
    root_actions = []

    for root in self._roots:
      root_uuid = uuid.uuid4().hex
      root_actions.append({
          "_index": self._index_name,
          "_type": self._efetch_doc_type,
          "_id": root_uuid,
          "_source": self._RootToDict(root, root_uuid)
      })

    helpers.bulk(self._elastic_db, root_actions)

    if len(self._efetch_queue) > 0:
      self._process_pool.apply_async(_ProcessEfetchEvents, args=(self._efetch_queue,
                                                                     self._efetch_time_queue,
                                                                     self._index_name,
                                                                     self._efetch_doc_type,
                                                                     self._elastic_host,
                                                                     self._elastic_port,
                                                                     self._image_id, self._image_path,
                                                                     self._output_mediator))
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
    self._roots.append(self._image_id)
    self._index_name = u'efetch_evidence_' + self._case_name

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
      logging.info('Total: %d Queue: %d', self._counter, len(self._efetch_event_queue))

    # Correlate filestat events to be used with Efetch
    if event_object.GetValues()['parser'] == 'filestat':
      if event_object.GetValues()['display_name'] not in self._efetch_event_queue:
        self._efetch_event_queue[event_object.GetValues()['display_name']] = {}
      if 'crtime' in event_object.GetValues()['timestamp_desc']:
        self._efetch_event_queue[event_object.GetValues()['display_name']]['crtime'] = event_object.timestamp
      if 'atime' in event_object.GetValues()['timestamp_desc']:
        self._efetch_event_queue[event_object.GetValues()['display_name']]['atime'] = event_object.timestamp
      if 'mtime' in event_object.GetValues()['timestamp_desc']:
        self._efetch_event_queue[event_object.GetValues()['display_name']]['mtime'] = event_object.timestamp
      if 'ctime' in event_object.GetValues()['timestamp_desc']:
        self._efetch_event_queue[event_object.GetValues()['display_name']]['ctime'] = event_object.timestamp
      if 'crtime' in self._efetch_event_queue[event_object.GetValues()['display_name']] and \
          'atime' in self._efetch_event_queue[event_object.GetValues()['display_name']] and \
          'mtime' in self._efetch_event_queue[event_object.GetValues()['display_name']] and \
          'ctime' in self._efetch_event_queue[event_object.GetValues()['display_name']]:
        self._efetch_queue.append(event_object)
        self._efetch_time_queue.append(self._efetch_event_queue[event_object.GetValues()['display_name']])
        root = event_object.GetValues()['display_name'].split(':/',1)[0]
        root = self._image_id + '/' + root.replace(':', '/')
        if root not in self._roots:
          self._roots.append(root)
        if len(self._efetch_queue) >= self._max_efetch_queue_size:
          self._process_pool.apply_async(_ProcessEfetchEvents, args=(copy.deepcopy(self._efetch_queue),
                                                                   copy.deepcopy(self._efetch_time_queue),
                                                                   self._index_name,
                                                                   self._efetch_doc_type,
                                                                   self._elastic_host,
                                                                   self._elastic_port,
                                                                   self._image_id, self._image_path,
                                                                   self._output_mediator))
          self._efetch_queue = []
          self._efetch_time_queue = []
          self._counter = self._counter + self._max_efetch_queue_size
          logging.info('Total: %d Queue: %d', self._counter, len(self._efetch_event_queue))
        del self._efetch_event_queue[event_object.GetValues()['display_name']]

  def WriteHeader(self):
    """Writes the header to the output."""
    self._elastic_db.indices.create(index='efetch_evidence', ignore=400)
    self._elastic_db.indices.put_template(name="efetch_evidence", body=evidence_template())

    sys.stdout.write('Inserting data')
    sys.stdout.flush()


def evidence_template():
  """Returns the Elastic Search mapping for Evidence"""
  return {
      'template': 'efetch_evidence*',
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
              'mtime':{'type': 'date', 'format': 'date_optional_time', 'index':'not_analyzed'},
              'atime':{'type': 'date', 'format': 'date_optional_time', 'index':'not_analyzed'},
              'ctime':{'type': 'date', 'format': 'date_optional_time', 'index':'not_analyzed'},
              'crtime':{'type': 'date', 'format': 'date_optional_time','index':'not_analyzed'},
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
    EfetchOutputModule, disabled=Elasticsearch is None)
