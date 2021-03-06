#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Default configuration for filenames, output directories and such."""

import logging
import os
import resource 
import shutil

__author__ = "Loic Jaquemet"
__copyright__ = "Copyright (C) 2012 Loic Jaquemet"
__email__ = "loic.jaquemet+python@gmail.com"
__license__ = "GPL"
__maintainer__ = "Loic Jaquemet"
__status__ = "Production"

log = logging.getLogger('config')


class ConfigClass():
  """Project-wide config class. """
  def __init__(self):
    #self.cacheDir = os.path.normpath(outputDir)
    #self.imgCacheDir = os.path.sep.join([self.cacheDir,'img'])
    self._WORDSIZE = None
    self.commentMaxSize = 64
    self.mmap_hack = True # bad bad idea...
    #
    self.DUMPNAME_INDEX_FILENAME = 'mappings'
    self.MAX_MAPPING_SIZE_FOR_MMAP = 1024*1024*20
    self.CACHE_NAME = 'cache'
    self.CACHE_STRUCT_DIR = 'structs'
    # cache file names
    self.CACHE_GENERATED_PY_HEADERS_VALUES = 'headers_values.py'
    self.CACHE_GENERATED_PY_HEADERS = 'headers.py'
    self.CACHE_HS_POINTERS_VALUES = 'heap+stack.pointers.values'
    self.CACHE_HEAP_ADDRS = 'heap.pointers.offsets'
    self.CACHE_HEAP_VALUES = 'heap.pointers.values'
    self.CACHE_STACK_ADDRS = 'stack.pointers.offsets'
    self.CACHE_STACK_VALUES = 'stack.pointers.values'
    self.CACHE_ALL_PTRS_ADDRS = 'all.pointers.offsets'
    self.CACHE_ALL_PTRS_VALUES = 'all.pointers.values'
    self.CACHE_FUNCTION_NAMES = 'names.pointers.functions'
    self.CACHE_STRUCTURES = 'structures'
    self.CACHE_MALLOC_CHUNKS_ADDRS = 'mchunks.addrs'
    self.CACHE_MALLOC_CHUNKS_SIZES = 'mchunks.sizes'
    self.CACHE_CONTEXT = 'ctx'
    self.CACHE_GRAPH = 'graph.gexf'
    self.DIFF_PY_HEADERS='diff_headers'
    self.CACHE_SIGNATURE_SIZES_DIR = 'structs.sizes.d'
    self.CACHE_SIGNATURE_SIZES_DIR_TAG = 'done'
    self.CACHE_SIGNATURE_GROUPS_DIR = 'structs.groups.d'
    self.REVERSED_TYPES_FILENAME = 'reversed_types.py'
    self.SIGNATURES_FILENAME = 'signatures'
    self.WORDS_FOR_REVERSE_TYPES_FILE = 'data/words.100'
    #others
    self._set_rlimits()
    
  def _set_rlimits(self):
    '''set rlimits to maximum allowed'''
    maxnofile = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (maxnofile[1], maxnofile[1]))
    return   
        
  def set_word_size(self, v):
    if self._WORDSIZE is not None and v != self._WORDSIZE:
      raise NotImplementedError('You should not change wordsize')
    #
    # TODO
    #
    import ctypes
    local = ctypes.sizeof( ctypes.c_void_p)
    if v != local :
      raise NotImplementedError('Haystack is not cross-arch. Local word is %d, target dump seems to be %d'%( local,v ))      
    #log.warning('Setting WORDTYPE size to %d'%(v))
    self._WORDSIZE = v
    # FIXME when multi arch
    # from haystack import model
    self.PTR_TYPE = type(ctypes.POINTER(Config.WORDTYPE)) # _ctypes.PyCPointerType    

  def get_word_size(self):
    ''' default config to local arch. you can change it. '''
    if self._WORDSIZE is None:
      # FIXME : Iam DROPPING THIS coz there no way we can do cross arch x32-x64 for now...
      #raise NotImplementedError('Please set_word_size(x) before.')
      import ctypes
      self.set_word_size( ctypes.sizeof(ctypes.c_void_p) )
    return self._WORDSIZE
  
  def get_word_type(self):
    import ctypes
    if self.WORDSIZE == 4:
      return ctypes.c_uint32
    elif self.WORDSIZE == 8:
      return ctypes.c_uint64
    else:
      raise ValueError('platform not supported for WORDSIZE == %d'%(self.WORDSIZE))
    return

  def get_word_type_char(self):
    if self.WORDSIZE == 4:
      return 'I'
    elif self.WORDSIZE == 8:
      return 'Q'
    else:
      raise ValueError('platform not supported for WORDSIZE == %d'%(self.WORDSIZE))
    return
    
  WORDSIZE = property(get_word_size, set_word_size)
  WORDTYPE = property(get_word_type)
  
  def makeCache(self, dumpname):
    root = os.path.abspath(dumpname)
    folder = os.path.sep.join([root, self.CACHE_NAME])
    if not os.access(folder, os.F_OK):    
      os.mkdir(folder)
    return
  
  def cleanCache(self, dumpname):
    root = os.path.abspath(dumpname)
    folder = os.path.sep.join([root, self.CACHE_NAME])
    if os.access(folder, os.F_OK):    
      shutil.rmtree(folder)
    return

  def getCacheName(self, dumpname):
    root = os.path.abspath(dumpname)
    return os.path.sep.join([root, self.CACHE_NAME])
    
  
  def getCacheFilename(self, typ, dumpname):
    '''Returns a filename for caching a type of data based on the dump filename.
  
    typ: one of Config.CACHE_XX types.
    dumpname: the dump file name.
    '''
    return os.path.sep.join([self.getCacheName(dumpname), typ])

  def getStructsCacheDir(self, dumpname):
    '''Returns a dirname for caching the structures based on the dump filename.
  
    dumpname: the dump file name.
    '''
    root = os.path.abspath(dumpname)
    return self.getCacheFilename(self.CACHE_STRUCT_DIR, root)


def make_config_from_memdump(dumpname):
  """ Load a memory dump meta data """
  index = open( os.path.sep.join( [dumpname, Config.DUMPNAME_INDEX_FILENAME] ), 'r' )
  m1 = index.readline().split(' ')
  # test if x32 or x64
  if len(m1[0]) > 10:
    log.info('[+] WORDSIZE = 8 #x64 arch dump detected')
    Config.set_word_size(8)
  else:
    Config.set_word_size(4)
  return 

Config = ConfigClass()

# FIXME set the word size and ptr_type
Config.get_word_size()

