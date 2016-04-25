# -*- coding: utf-8 -*-
"""An output module that saves data into an ElasticSearch database."""

import logging
import sys
import uuid
import os
import copy
import time
from plaso.serializer import json_serializer
from multiprocessing import Process, Pool
from plaso.serializer import json_serializer
from dfvfs.lib import definitions as dfvfs_definitions

try:
  import requests
  import pyelasticsearch
except ImportError:
  pyelasticsearch = None

from plaso.lib import errors
from plaso.lib import timelib
from plaso.output import interface
from plaso.output import manager
from dfvfs.resolver import resolver
from dfvfs.serializer.json_serializer import JsonPathSpecSerializer

def _ProcessEvents(queue, index_name, doc_type, elastic_host, elastic_port, image_id, image_path, output_mediator):
  data = []
  while queue:
    event_object = queue.pop(0)
    try:
      data.append(_EventToDict(event_object, image_id, image_path, output_mediator))
    except Exception as e:
      logging.warn('Failed to add event ' + event_object.GetValues()['display_name'])
      logging.warn('Because: ' + e.message)
  elastic_db = pyelasticsearch.ElasticSearch(u'http://{0:s}:{1:d}'.format(elastic_host, elastic_port))
  elastic_db.bulk_index(index_name, doc_type, data)
  logging.info('Finished 32000 Events')
  return

def _ProcessEfetchEvents(queue, efetch_time_queue, index_name, doc_type, elastic_host, elastic_port, image_id,
                         image_path, output_mediator):
  data = []
  while queue:
    event_object = queue.pop(0)
    try:
      data.append(_EventToEfetch(event_object, efetch_time_queue.pop(0),
                                 image_id, image_path, output_mediator))
    except Exception as e:
      logging.warn('Failed to add event ' + event_object.GetValues()['display_name'])
      logging.warn('Because: ' + e.message)
  elastic_db = pyelasticsearch.ElasticSearch(u'http://{0:s}:{1:d}'.format(elastic_host, elastic_port))
  elastic_db.bulk_index(index_name, doc_type, data)
  logging.info('Finished 500 Efetch Events')
  return

def _EventToDict(event_object, image_id, image_path, output_mediator):
  """Returns a dict built from an event object.

  Args:
    event_object: the event object (instance of EventObject).
  """
  ret_dict = event_object.GetValues()

  #EFETCH CHANGES###########################################
  #parent = (json_serializer._EventObjectJSONEncoder())._ConvertPathSpecToDict(ret_dict['pathspec'])
  ret_dict['image_id'] = image_id

  #if not image_path:
  #  while 'parent' in parent:
  #    parent = parent['parent']
  #  image_path = parent['location']
  #ret_dict['image_path'] = image_path

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
  ret_dict['path'] = path
  ret_dict['ext'] = ext.lower()
  ret_dict['image_id'] = image_id
  if 'pathspec' in ret_dict:
    ret_dict['pathspec'] = JsonPathSpecSerializer.WriteSerialized(ret_dict['pathspec'])
  ##########################################################

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

  return ret_dict

def _EventToEfetch(event_object, event_times, image_id, image_path, output_mediator):
  """Returns a dict built from an event object.

  Args:
    event_object: the event object (instance of EventObject).
  """
  ret_dict = event_object.GetValues()
  #TODO This has the all important location variable I need...
  #       it is currently nested so I might need to flatten the json
  # Get rid of few attributes that cause issues (and need correcting).
  #EFETCH CHANGES###########################################
  #parent = (json_serializer._EventObjectJSONEncoder())._ConvertPathSpecToDict(ret_dict['pathspec'])
  ret_dict['image_id'] = image_id

  #if not image_path:
  #  while 'parent' in parent:
  #    parent = parent['parent']
  #  image_path = parent['location']
  #ret_dict['image_path'] = image_path

  #ret_dict['image_id'] = image_id

  # Don't know how I feel about this split... :/ Meh
  root, path = ret_dict['display_name'].split(':/',1)
  path = '/' + path
  root = image_id + '/' + root.replace(':', '/')
  pid = root + path
  name = os.path.basename(path)
  directory = os.path.dirname(pid) + '/'
  ext = os.path.splitext(name)[1][1:] or ""

  #if root not in roots:
  #  roots.append(root)

  if 'inode' in ret_dict:
    iid = root + '/' + str(ret_dict['inode'])
  else:
    iid = root + '/none'

  #if pid in ids:
  # logging.warn('_ID %s already exists', pid)
  #  return
  #else:
  #  ids.append(pid)

  ret_dict['root'] = root
  ret_dict['id'] = pid
  ret_dict['pid'] = pid
  ret_dict['name'] = name
  ret_dict['dir'] = directory
  ret_dict['path'] = path
  ret_dict['ext'] = ext.lower()
  ret_dict['iid'] = iid
  ret_dict['driver'] = 'fa_dfvfs'
  ret_dict['parser'] = 'efetch'

  #if 'pathspec' in ret_dict:
  #  decoded_path_spec = ret_dict['pathspec']
  #  file_entry = resolver.Resolver.OpenFileEntry(decoded_path_spec)
  #  ret_dict['parent'] = file_entry.number_of_sub_file_entries
  #  ret_dict['pathspec'] = JsonPathSpecSerializer.WriteSerialized(ret_dict['pathspec'])

  if 'pathspec' in ret_dict:
    ret_dict['pathspec'] = JsonPathSpecSerializer.WriteSerialized(ret_dict['pathspec'])

  #if 'tag' in ret_dict:
  #  del ret_dict['tag']
  #  tag = getattr(event_object, 'tag', None)
  #  if tag:
  #    tags = tag.tags
  #    ret_dict['tag'] = tags
  #    if getattr(tag, 'comment', ''):
  #      ret_dict['comment'] = tag.comment
  ret_dict['tag'] = []

  if 'timestamp_desc' in ret_dict:
    del ret_dict['timestamp_desc']

  # Adding attributes in that are calculated/derived.
  # We want to remove millisecond precision (causes some issues in
  # conversion).
  #ret_dict['datetime'] = timelib.Timestamp.CopyToIsoFormat(
  #    timelib.Timestamp.RoundToSeconds(event_object.timestamp),
  #    timezone=output_mediator.timezone)
  for time_attribute in ['atime', 'ctime', 'crtime', 'mtime']:
    ret_dict[time_attribute] = timelib.Timestamp.CopyToIsoFormat(
          timelib.Timestamp.RoundToSeconds(event_times[time_attribute]),
          timezone=output_mediator.timezone)

  #message, _ = output_mediator.GetFormattedMessages(event_object)
  #if message is None:
  #  raise errors.NoFormatterFound(
  #      u'Unable to find event formatter for: {0:s}.'.format(
  #          getattr(event_object, u'data_type', u'UNKNOWN')))
  #
  #ret_dict['message'] = message

  #source_short, source = output_mediator.GetFormattedSources(
  #    event_object)
  #if source is None or source_short is None:
  #  raise errors.NoFormatterFound(
  #      u'Unable to find event formatter for: {0:s}.'.format(
  #          getattr(event_object, u'data_type', u'UNKNOWN')))

  #ret_dict['source_short'] = source_short
  #ret_dict['source_long'] = source

  hostname = output_mediator.GetHostname(event_object)
  ret_dict['hostname'] = hostname

  username = output_mediator.GetUsername(event_object)
  ret_dict['username'] = username

  return ret_dict

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
    self._max_processes = 8
    self._queue = []
    self._process_pool = Pool(processes=self._max_processes)
    self._efetch_queue = []
    self._efetch_time_queue = []
    self._data = []
    self._doc_type = None
    self._elastic_db = None
    self._index_name = None
    self._image_id = None
    self._image_id_value = None
    self._uuid = None
    self._roots = []
    self._efetch_event_queue = {}
    self._image_path = None
    self._ids = []
    self._elastic_port = None
    self._elastic_host = None

  def _RootToDict(self, root):
    sections = root.split('/')
    dictionary = {}
    dictionary['image_id'] = sections[0]
    dictionary['pid'] = root
    if root in self._ids:
      logging.warn('_ID %s already exists', dictionary['pid'])
      return
    else:
      self._ids.append(root)
    dictionary['id'] = root
    dictionary['dir'] = '/'.join(sections[:-1]) + '/'
    dictionary['path'] = root
    dictionary['iid'] = root + '/'
    dictionary['name'] = sections[-1]
    dictionary['image_path'] = self._image_path
    dictionary['size'] = 0
    dictionary['ext'] = ''
    dictionary['datetime'] = 0
    dictionary['parser'] = 'efetch'
    dictionary['meta_type'] = 'Directory'
    return dictionary

  def Close(self):
    """Disconnects from the elastic search server."""
    root_data = []
    for root in self._roots:
        root_data.append(self._RootToDict(root))
    self._elastic_db.bulk_index(self._index_name, self._doc_type, root_data)
    if len(self._efetch_queue) > 0:
          self._process_pool.apply_async(_ProcessEfetchEvents, args=(self._efetch_queue,
                                                                   self._efetch_time_queue,
                                                                   self._index_name,
                                                                   self._doc_type,
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
    self._uuid = uuid.uuid4().hex
    self._image_id = self._uuid
    self._roots.append(self._image_id)
    self._index_name = u'efetch_evidence_' + self._uuid

  def SetDocumentType(self, document_type):
    """Set the document type for the ElasticSearch database connection.

    Args:
      document_type: the document type for the ElasticSearch database.
    """
    if document_type:
      self._doc_type = document_type.lower()
    else:
      self._doc_type = u'event'

  def SetServerInformation(self, elastic_host, elastic_port):
    """Set the ElasticSearch connection.

    Args:
      elastic_host: the hostname or IP address of the ElasticSearch server.
      elastic_port: the port number that the ElasticSearch is listening on.
    """
    self._elastic_host = elastic_host
    self._elastic_port = elastic_port
    self._elastic_db = pyelasticsearch.ElasticSearch(
        u'http://{0:s}:{1:d}'.format(elastic_host, elastic_port))

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

    #EFETCH#####
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
                                                                   self._doc_type,
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
    mapping = {
        self._doc_type: {
            u'properties': {
                u'date': {
                    u'type': 'date',
                    u'format': 'epoch_second'
                }
             }
        }
    }
    # Check if the mappings exist (only create if not there).
    try:
      old_mapping_index = self._elastic_db.get_mapping(self._index_name)
      old_mapping = old_mapping_index.get(self._index_name, {})
      if self._doc_type not in old_mapping:
        self._elastic_db.put_mapping(
            self._index_name, self._doc_type, mapping=mapping)
    except (pyelasticsearch.ElasticHttpNotFoundError,
            pyelasticsearch.exceptions.ElasticHttpError):
      try:
        self._elastic_db.create_index(self._index_name, settings={
            'mappings': mapping})
      except pyelasticsearch.IndexAlreadyExistsError:
        raise RuntimeError(u'Unable to created the index')
    except requests.exceptions.ConnectionError as exception:
      logging.error(
          u'Unable to proceed, cannot connect to ElasticSearch backend '
          u'with error: {0:s}.\nPlease verify connection.'.format(exception))
      raise RuntimeError(u'Unable to connect to ElasticSearch backend.')

    # pylint: disable=unexpected-keyword-arg
    self._elastic_db.health(wait_for_status='yellow')

    sys.stdout.write('Inserting data')
    sys.stdout.flush()


manager.OutputManager.RegisterOutput(
    EfetchOutputModule, disabled=pyelasticsearch is None)
