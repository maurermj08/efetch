# -*- coding: utf-8 -*-
"""An output module that saves data into an ElasticSearch database."""
#TODO Recreate as the all mighty Efetch Output
#       TODO: Update Index Name
#       TODO: Assure that the location is there
#       ????: Wouldn't it be cool if we could change the
#               display name to match what I am use to
#               and possibly add multiple instances
#               for Kibana


import logging
import sys
import uuid
import os
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
    self._data = []
    self._doc_type = None
    self._elastic_db = None
    self._index_name = None
    self._image_id = None
    self._roots = []
    self._efetch_event_queue = {}
    self._image_path = None

  def _EventToDict(self, event_object):
    """Returns a dict built from an event object.

    Args:
      event_object: the event object (instance of EventObject).
    """
    ret_dict = event_object.GetValues()

    #EFETCH CHANGES###########################################
    parent = (json_serializer._EventObjectJSONEncoder())._ConvertPathSpecToDict(ret_dict['pathspec'])
    ret_dict['image_id'] = self._image_id 
    
    if not self._image_path:
      while 'parent' in parent:
        parent = parent['parent']
      self._image_path = parent['location']
    ret_dict['image_path'] = self._image_path

    ret_dict['image_id'] = self._image_id
    ##########################################################

    if 'pathspec' in ret_dict:
      del ret_dict['pathspec']

    #if 'tag' in ret_dict:
    #  del ret_dict['tag']
    #  tag = getattr(event_object, 'tag', None)
    #  if tag:
    #    tags = tag.tags
    #    ret_dict['tag'] = tags
    #    if getattr(tag, 'comment', ''):
    #      ret_dict['comment'] = tag.comment
    ret_dict['tag'] = []

    # To not overload the index, remove the regvalue index.
    if 'regvalue' in ret_dict:
      del ret_dict['regvalue']

    # Adding attributes in that are calculated/derived.
    # We want to remove millisecond precision (causes some issues in
    # conversion).
    ret_dict['datetime'] = timelib.Timestamp.CopyToIsoFormat(
        timelib.Timestamp.RoundToSeconds(event_object.timestamp),
        timezone=self._output_mediator.timezone)

    message, _ = self._output_mediator.GetFormattedMessages(event_object)
    if message is None:
      raise errors.NoFormatterFound(
          u'Unable to find event formatter for: {0:s}.'.format(
              getattr(event_object, u'data_type', u'UNKNOWN')))

    ret_dict['message'] = message

    source_short, source = self._output_mediator.GetFormattedSources(
        event_object)
    if source is None or source_short is None:
      raise errors.NoFormatterFound(
          u'Unable to find event formatter for: {0:s}.'.format(
              getattr(event_object, u'data_type', u'UNKNOWN')))

    ret_dict['source_short'] = source_short
    ret_dict['source_long'] = source

    hostname = self._output_mediator.GetHostname(event_object)
    ret_dict['hostname'] = hostname

    username = self._output_mediator.GetUsername(event_object)
    ret_dict['username'] = username

    return ret_dict

  def _EventToEfetch(self, event_object, event_times):
    """Returns a dict built from an event object.

    Args:
      event_object: the event object (instance of EventObject).
    """
    ret_dict = event_object.GetValues()
    #TODO This has the all important location variable I need... 
    #       it is currently nested so I might need to flatten the json
    # Get rid of few attributes that cause issues (and need correcting).
    #EFETCH CHANGES###########################################
    parent = (json_serializer._EventObjectJSONEncoder())._ConvertPathSpecToDict(ret_dict['pathspec'])
    ret_dict['image_id'] = self._image_id 
    
    if not self._image_path:
      while 'parent' in parent:
        parent = parent['parent']
      self._image_path = parent['location']
    ret_dict['image_path'] = self._image_path

    ret_dict['image_id'] = self._image_id

    # Don't know how I feel about this split... :/ Meh
    root, path = ret_dict['display_name'].split(':/',1)   
    path = '/' + path
    root = self._image_id + '/' + root.replace(':', '/')
    pid = root + path
    name = os.path.basename(path)
    directory = os.path.dirname(pid) + '/'
    ext = os.path.splitext(name)[1][1:] or ""

    #file_entry = resolver.Resolver.OpenFileEntry(ret_dict['pathspec'])
    #stat_object = file_entry.GetStat()
    #if stat_object:
    #  for time_attribute in [u'atime', u'bkup_time', u'ctime', u'crtime', u'dtime', u'mtime']:
    #    posix_time = getattr(stat_object, time_attribute, None)
    #    if posix_time is None:
    #      continue
    #
    #    nano_time_attribute = u'{0:s}_nano'.format(time_attribute)
    #    nano_time_attribute = getattr(stat_object, nano_time_attribute, None)
    #
    #    timestamp = timelib.Timestamp.FromPosixTime(posix_time)
    #    if nano_time_attribute is not None:
    #      # Note that the _nano values are in intervals of 100th nano seconds.
    #      micro_time_attribute, _ = divmod(nano_time_attribute, 10)
    #      timestamp += micro_time_attribute
    #
    #    # TSK will return 0 if the timestamp is not set.
    #    if (file_entry.type_indicator == dfvfs_definitions.TYPE_INDICATOR_TSK and
    #        not timestamp):
    #      continue
    #
    #    ret_dict[time_attribute] = timestamp

    if root not in self._roots:
      self._roots.append(root)

    if 'inode' in ret_dict:
      iid = root + '/' + str(ret_dict['inode']) 
    else:
      iid = root + '/none'

    ret_dict['root'] = root
    ret_dict['pid'] = pid
    ret_dict['name'] = name
    ret_dict['dir'] = directory
    ret_dict['path'] = path
    ret_dict['ext'] = ext
    ret_dict['iid'] = iid
    ret_dict['driver'] = 'fa_dfvfs'
    ret_dict['parser'] = 'efetch'
    ##########################################################

    if 'pathspec' in ret_dict:
      del ret_dict['pathspec']
  
    #if 'tag' in ret_dict:
    #  del ret_dict['tag']
    #  tag = getattr(event_object, 'tag', None)
    #  if tag:
    #    tags = tag.tags
    #    ret_dict['tag'] = tags
    #    if getattr(tag, 'comment', ''):
    #      ret_dict['comment'] = tag.comment
    ret_dict['tag'] = []

    # To not overload the index, remove the regvalue index.
    if 'regvalue' in ret_dict:
      del ret_dict['regvalue']

    # Adding attributes in that are calculated/derived.
    # We want to remove millisecond precision (causes some issues in
    # conversion).
    #ret_dict['datetime'] = timelib.Timestamp.CopyToIsoFormat(
    #    timelib.Timestamp.RoundToSeconds(event_object.timestamp),
    #    timezone=self._output_mediator.timezone)
    for time_attribute in ['atime', 'ctime', 'crtime', 'mtime']:   
      ret_dict[time_attribute] = timelib.Timestamp.CopyToIsoFormat(
          timelib.Timestamp.RoundToSeconds(event_times[time_attribute]),
          timezone=self._output_mediator.timezone)

    message, _ = self._output_mediator.GetFormattedMessages(event_object)
    if message is None:
      raise errors.NoFormatterFound(
          u'Unable to find event formatter for: {0:s}.'.format(
              getattr(event_object, u'data_type', u'UNKNOWN')))

    ret_dict['message'] = message

    source_short, source = self._output_mediator.GetFormattedSources(
        event_object)
    if source is None or source_short is None:
      raise errors.NoFormatterFound(
          u'Unable to find event formatter for: {0:s}.'.format(
              getattr(event_object, u'data_type', u'UNKNOWN')))

    ret_dict['source_short'] = source_short
    ret_dict['source_long'] = source

    hostname = self._output_mediator.GetHostname(event_object)
    ret_dict['hostname'] = hostname

    username = self._output_mediator.GetUsername(event_object)
    ret_dict['username'] = username

    return ret_dict

  def RootToDict(self, root):
    sections = root.split('/')
    dictionary = {}
    dictionary['image_id'] = sections[0]
    dictionary['pid'] = root
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
    for root in self._roots:
        self._data.append(self.RootToDict(root))
    self._elastic_db.bulk_index(self._index_name, self._doc_type, self._data)
    self._data = []
    sys.stdout.write('. [DONE]\n')
    sys.stdout.write('ElasticSearch index name: {0:s}\n'.format(
        self._index_name))
    sys.stdout.flush()

  #CONVERT TO IMAGE_NAME
  def SetCaseName(self, case_name):
    """Set the case name for the ElasticSearch database connection.

    Args:
      case_name: the case name, used for the name of the index in the database.
    """
    #TODO: That index should be named nicely, like Efetch_ImageName
    #      Maybe just prompt for it! O_O BOOM! There it is!
    self._image_id = raw_input('Please specify an image name: ').lower()
    self._roots.append(self._image_id)
    self._index_name = 'efetch-evidence_' + self._image_id
    #if case_name:
    #  self._index_name = case_name.lower()
    #else:
    #  self._index_name = uuid.uuid4().hex

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
    self._elastic_db = pyelasticsearch.ElasticSearch(
        u'http://{0:s}:{1:d}'.format(elastic_host, elastic_port))

  def WriteEventBody(self, event_object):
    """Writes the body of an event object to the output.

    Args:
      event_object: the event object (instance of EventObject).
    """
    self._data.append(self._EventToDict(event_object))
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
        self._data.append(self._EventToEfetch(event_object, self._efetch_event_queue[event_object.GetValues()['display_name']]))
        del self._efetch_event_queue[event_object.GetValues()['display_name']]
    
    logging.info('Number of values in Efetch Queue: ' + str(len(self._efetch_event_queue)))
    ############
    self._counter += 1

    # Check if we need to flush.
    if self._counter % 5000 == 0:
      self._elastic_db.bulk_index(self._index_name, self._doc_type, self._data)
      self._data = []
      sys.stdout.write('.')
      sys.stdout.flush()

  def WriteHeader(self):
    """Writes the header to the output."""
    mapping = {
        self._doc_type: {
            u'properties': {
                u'date': {
                    u'type': 'date',
                    u'format': 'epoch_second'}
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
    ElasticSearchOutputModule, disabled=pyelasticsearch is None)
