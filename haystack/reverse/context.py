#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import numpy
import os
import pickle

from haystack.config import Config
from haystack.reverse import utils

__author__ = "Loic Jaquemet"
__copyright__ = "Copyright (C) 2012 Loic Jaquemet"
__license__ = "GPL"
__maintainer__ = "Loic Jaquemet"
__email__ = "loic.jaquemet+python@gmail.com"
__status__ = "Production"


log = logging.getLogger('context')


class ReverserContext(): 
  ''' TODO: Change Name to MmapReverserContext
  add methods for chained mmap
  Add check for context, only on valid heaps ( getHeaps)
  '''
  def __init__(self, mappings, heap):
    self.mappings = mappings
    self.dumpname = mappings.name
    self.heap = heap
    self._heap_start = heap.start
    self.parsed = set()
    self._function_names = dict()
    # refresh heap pointers list and allocators chunks
    self._init2()
    return

  def _init2(self):
    # force reload JIT
    self._reversedTypes = dict()
    self._structures = None
    ructures = None

    log.info('[+] Fetching cached structures addresses list')
    #ptr_values, ptr_offsets, aligned_ptr, not_aligned_ptr = utils.getHeapPointers(self.dumpname, self.mappings)
    
    ## FIXME: no use I think
    ##heap_offsets, heap_values = utils.getHeapPointers(self.dumpname, self.mappings)
    ##self._pointers_values_heap = heap_values
    ##self._pointers_offsets_heap = heap_offsets

    # test with all mmap in target
    ##all_offsets, all_values = utils.getAllPointers(self.dumpname, self.mappings) 
    ##self._pointers_values = all_values
    ##self._pointers_offsets = all_offsets
    
    if self.mappings._target_system != 'win32':
      log.info('[+] Reversing function pointers names')
      from haystack.reverse.libc import libdl
      self._function_names = dict() #TODO INLINE CACHED dict(libdl.reverseLocalFonctionPointerNames(self) )
    
    log.info('[+] Fetching cached malloc chunks list')
    # malloc_size is the structures_sizes, 
    # TODO adaptable allocator win32/linux
    self._malloc_addresses, self._malloc_sizes = utils.getAllocations(self.dumpname, self.mappings, self.heap)
    self._structures_addresses = self._malloc_addresses
    self._user_alloc_addresses = self._malloc_addresses
    self._user_alloc_sizes = self._malloc_sizes

    return 

  def has_allocations(self):
    ''' allocation based mmap '''
    return True
  
  def getStructureForAddr(self, addr):
    ''' return the structure.AnonymousStructInstance associated with this addr'''
    return self._get_structures()[addr]

  ''' TODO implement a LRU cache '''
  def _get_structures(self):
    #### TODO use HeapWalker ... win32 + libc
    if self._structures is not None and len(self._structures) == len(self._malloc_addresses):
      return self._structures
    # cache Load
    from haystack.reverse import structure, reversers
    log.info('[+] Fetching cached structures list')
    self._structures = dict([ (long(vaddr),s) for vaddr,s in structure.cacheLoadAllLazy(self) ])
    log.info('[+] Fetched %d cached structures addresses from disk'%( len(self._structures) ))

    if len(self._structures) != len(self._malloc_addresses): # no all structures yet, make them from MallocReverser
      log.info('[+] No cached structures - making them from malloc reversers %d|%d'%
                      (len(self._structures) ,len(self._malloc_addresses)))
      if ( len(self._malloc_addresses) - len(self._structures) ) < 10 :
        log.warning('close numbers to check %s'%(set( self._malloc_addresses ) - set( self._structures ) ))
        self.parsed = set()
      # use GenericHeapAllocationReverser to get user blocks
      mallocRev = reversers.GenericHeapAllocationReverser()
      context = mallocRev.reverse(self)
      #mallocRev.check_inuse(self)
      log.info('[+] Built %d/%d structures from malloc blocs'%( len(self._structures) , len(self._malloc_addresses) ))
    
    return self._structures

  def getStructureSizeForAddr(self, addr):
    ''' return the structure.AnonymousStructInstance associated with this addr'''
    itemindex=numpy.where(self._malloc_addresses == numpy.int64(addr))[0][0]
    return self._malloc_sizes[itemindex]

  def structuresCount(self):
    if self._structures is not None and len(self._structures) == len(self._malloc_addresses):
      return len(self._get_structures())
    return len(self._malloc_addresses)

  def getStructureAddrForOffset(self, offset):
    '''Returns the closest containing structure address for this offset in this heap.'''
    #if offset not in self.heap:
    #  raise ValueError('address 0x%0.8x not in heap 0x%0.8x'%(offset, self.heap.start))
    return utils.closestFloorValue(offset, self._structures_addresses)[0] # [1] is the index of [0]

  def getStructureForOffset(self, ptr_value):
    '''Returns the structure containing this address'''
    st = self.getStructureForAddr(self.getStructureAddrForOffset(ptr_value))
    if st._vaddr <= ptr_value < (st._vaddr + len(st)):
      return st
    raise IndexError('No known structure covers that ptr_value') 

  def listOffsetsForPointerValue(self, ptr_value):
    '''Returns the list of offsets where this value has been found'''
    return [int(self._pointers_offsets[offset]) for offset in numpy.where(self._pointers_values==ptr_value)[0]]

  def listPointerValueInHeap(self):
    '''Returns the list of pointers found in the heap'''
    return map(long, self._pointers_values)

  def listStructuresAddrForPointerValue(self, ptr_value):
    '''Returns the list of structures addresses with a member with this pointer value '''
    return sorted(set([ int(self.getStructureAddrForOffset(offset)) for offset in self.listOffsetsForPointerValue(ptr_value)]))

  def listStructuresForPointerValue(self, ptr_value):
    '''Returns the list of structures with a member with this pointer value '''
    return [ self._get_structures()[addr] for addr in self.listStructuresAddrForPointerValue(ptr_value)]
  
  def listStructuresAddresses(self):
    return map(long,self._get_structures().keys())

  def listStructures(self):
    return self._get_structures().values()

  def getReversedType(self, typename):
    if typename in self._reversedTypes:
      return self._reversedTypes[ typename ]
    return None

  def addReversedType(self, typename, t):
    self._reversedTypes[ typename ] = t

  def listReversedTypes(self):
    return self._reversedTypes.values()
    
  @classmethod
  def cacheLoad(cls, mappings):
    #from haystack.reverse.context import ReverserContext
    dumpname = os.path.normpath(mappings.name)
    Config.makeCache(dumpname)
    context_cache = Config.getCacheFilename(Config.CACHE_CONTEXT, dumpname)
    try:
      context = pickle.load(file(context_cache,'r'))
    except EOFError,e:
      os.remove(context_cache)
      log.error('Error in the context file. File cleaned. Please restart.')
      raise e
    log.debug('\t[-] loaded my context from cache')
    context.mappings = mappings
    context.heap = context.mappings.getMmapForAddr(context._heap_start) 
    
    context._init2()
    return context
    
  
  def save(self):
    # we only need dumpfilename to reload mappings, addresses to reload cached structures
    context_cache = Config.getCacheFilename(Config.CACHE_CONTEXT, self.dumpname)
    pickle.dump(self, file(context_cache,'w'))

  def reset(self):
    try:
      os.remove(Config.getCacheFilename(Config.CACHE_CONTEXT, self.dumpname) ) 
    except OSError,e:
      pass
    try:
      if not os.access(Config.CACHE_STRUCT_DIR, os.F_OK):
        return
      for r,d,files in os.walk( Config.getCacheFilename(Config.CACHE_STRUCT_DIR, self.dumpname)):
        for f in files:
          os.remove(os.path.join(r,f) )
      os.rmdir(r)
    except OSError,e:
      pass
  
  def __getstate__(self):
    d = self.__dict__.copy()
    del d['mappings']
    del d['heap']

    del d['_structures']
    del d['_structures_addresses']
    #del d['_pointers_values']
    #del d['_pointers_offsets']
    del d['_malloc_addresses']
    del d['_malloc_sizes']
    #print d
    return d

  def __setstate__(self, d):
    self.dumpname = d['dumpname']
    self.parsed = d['parsed']
    self._heap_start = d['_heap_start']
    self._structures = None
    self._function_names = dict()
    return
  

def get_context(fname):
  ''' Load a dump file, and create a reverser context object.
  @return context: a ReverserContext
  '''
  from haystack import dump_loader
  mappings = dump_loader.load( fname)  
  try:
    context = ReverserContext.cacheLoad(mappings)
  except IOError,e:
    context = ReverserContext(mappings, mappings.getHeap())  
  # cache it
  context.heap._context = context
  return context




if __name__ == '__main__':
  pass
