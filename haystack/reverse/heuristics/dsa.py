#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Loic Jaquemet loic.jaquemet+python@gmail.com
#

import logging
import os
import array
import struct
import itertools

from haystack.config import Config
from haystack.utils import unpackWord
from haystack.reverse import re_string, fieldtypes
from haystack.reverse.fieldtypes import FieldType, Field, PointerField
from haystack.reverse.heuristics.model import FieldAnalyser, StructureAnalyser

import ctypes

log = logging.getLogger('dsa')

## Field analysis related functions and classes

class ZeroFields(FieldAnalyser):
  ''' checks for possible fields, aligned, with WORDSIZE zeros.'''
  def make_fields(self, structure, offset, size):
    assert( offset%Config.WORDSIZE == 0 ) #vaddr and offset should be aligned
    #log.debug('checking Zeroes')
    self._typename = FieldType.ZEROES
    self._zeroes = '\x00'*Config.WORDSIZE

    ret = self._find_zeroes(structure, offset, size)
    
    # TODO if its just a word, we should say its a small int.
    return ret  
  
  def _find_zeroes(self, structure, offset, size):
    ''' iterate over the bytes until a byte if not \x00 
    '''
    bytes = structure.bytes
    #print 'offset:%x blen:%d'%(offset, len(bytes))
    #print repr(bytes)
    assert( (offset)%Config.WORDSIZE == 0 )
    #aligned_off = (offset)%Config.WORDSIZE 
    start = offset
    #if aligned_off != 0: # align to next
    #  start += (Config.WORDSIZE - aligned_off)
    #  size  -= (Config.WORDSIZE - aligned_off)
    # iterate
    matches = array.array('i')
    for i in range(start, start+size, Config.WORDSIZE ):
      # PERF TODO: bytes or struct test ?
      #print repr(bytes[start+i:start+i+Config.WORDSIZE])
      if bytes[start+i:start+i+Config.WORDSIZE] == self._zeroes:
        matches.append(start+i)
        #print matches
    # collate
    if len(matches) == 0:
      return []
    # lets try to get fields
    fields = []
    # first we need to collate neighbors
    collates = list()
    prev = matches[0]-Config.WORDSIZE
    x = []
    # PERF TODO: whats is algo here
    for i in matches:
      if i-Config.WORDSIZE == prev:
        x.append(i)
      else:
        collates.append(x)
        x = [i]
      prev = i
    collates.append(x)
    #log.debug(collates)
    # we now have collated, lets create fields
    for field in collates:
      flen = len(field)
      if flen > 1:
        size = Config.WORDSIZE * flen
      elif flen == 1:
        size = Config.WORDSIZE
      else:
        continue
      # make a field
      fields.append( Field(structure, start+field[0], self._typename, size, False) ) 
    # we have all fields
    return fields

class UTF16Fields(FieldAnalyser):
  ''' rfinds utf-16-ascii and ascii 7bit
  
  '''
  def make_fields(self, structure, offset, size):
    assert( offset%Config.WORDSIZE == 0 ) #vaddr and offset should be aligned
    #log.debug('checking String')
    fields = []
    bytes = structure.bytes
    while size > Config.WORDSIZE:
      #print 're_string.rfind_utf16(bytes, %d, %d)'%(offset,size)
      index = re_string.rfind_utf16(bytes, offset, size)
      if index > -1:
        f = Field(structure, offset+index, FieldType.STRING16, size-index, False)  
        #print repr(structure.bytes[f.offset:f.offset+f.size])
        fields.append(f)
        size = index # reduce unknown field in prefix
      else:
        size -= Config.WORDSIZE # reduce unkown field
    # look in head
    return fields
  
class PrintableAsciiFields(FieldAnalyser):
  ''' finds printable ascii fields '''
  def make_fields(self, structure, offset, size):
    assert( offset%Config.WORDSIZE == 0 ) #vaddr and offset should be aligned
    #log.debug('checking String')
    fields = []
    bytes = structure.bytes
    while size >= Config.WORDSIZE:
      #print 're_string.find_ascii(bytes, %d, %d)'%(offset,size)
      index, ssize = re_string.find_ascii(bytes, offset, size)
      if index == 0:
        if (ssize < size) and bytes[offset+index+ssize]=='\x00': # space for a \x00
          ssize +=1
          f = Field(structure, offset+index, FieldType.STRINGNULL, ssize, False)  
        else:
          f = Field(structure, offset+index, FieldType.STRING, ssize, False)  
        #print repr(structure.bytes[f.offset:f.offset+f.size])
        fields.append(f)
        size -= ssize # reduce unknown field
        offset += ssize
        if ssize%Config.WORDSIZE:
          rest = Config.WORDSIZE - ssize%Config.WORDSIZE
          size -= rest # goto next aligned
          offset += rest
      else:
        size -= Config.WORDSIZE # reduce unkown field
        offset += Config.WORDSIZE
    # look in head
    return fields
  


class PointerFields(FieldAnalyser):
  ''' TODO tests '''
  ''' looks at a word for a pointer value'''
  def make_fields(self, structure, offset, size):
    # iterate on all offsets . NOT assert( size == Config.WORDSIZE)
    assert( offset%Config.WORDSIZE == 0 ) #vaddr and offset should be aligned
    log.debug('checking Pointer')
    bytes = structure.bytes
    fields = []
    while size >= Config.WORDSIZE:
      value = unpackWord(bytes[offset:offset+Config.WORDSIZE])
      # check if pointer value is in range of mappings and set self.comment to pathname value of pointer
      # TODO : if bytes 1 & 3 == \x00, maybe utf16 string
      if value not in structure._mappings:
        size -= Config.WORDSIZE
        offset += Config.WORDSIZE
        continue
      # we have a pointer
      log.debug('checkPointer offset:%s value:%s'%(offset, hex(value)))
      field = PointerField(structure, offset, FieldType.POINTER, Config.WORDSIZE, False)  
      field.value = value
      # TODO: leverage the context._function_names 
      if value in structure._context._function_names :
        field.comment = ' %s::%s'%(os.path.basename(structure._mappings.getMmapForAddr(value).pathname), 
                    structure._context._function_names[value])
      else:
        field.comment = structure._mappings.getMmapForAddr(value).pathname 
      fields.append(field)
      size -= Config.WORDSIZE
      offset += Config.WORDSIZE
    return fields



class IntegerFields(FieldAnalyser):
  ''' looks at a word for a small int value'''
  def make_fields(self, structure, offset, size):
    # iterate on all offsets . NOT assert( size == Config.WORDSIZE)
    assert( offset%Config.WORDSIZE == 0 ) #vaddr and offset should be aligned
    #log.debug('checking Integer')
    bytes = structure.bytes
    fields = []
    while size >= Config.WORDSIZE:
      #print 'checking >'
      field = self.checkSmallInt(structure, bytes, offset)
      if field is None:
        #print 'checking <'
        field = self.checkSmallInt(structure, bytes, offset, '>')
      # we have a field smallint
      if field is not None:
        fields.append(field)      
      size -= Config.WORDSIZE
      offset += Config.WORDSIZE
    return fields

  def checkSmallInt(self, structure, bytes, offset, endianess='<'):
    ''' check for small value in signed and unsigned forms '''
    val = unpackWord(bytes[offset:offset+Config.WORDSIZE], endianess)
    #print endianess, val
    if val < 0xffff:
      field = Field(structure, offset, FieldType.SMALLINT, Config.WORDSIZE, False)
      field.value = val
      field.endianess = endianess
      return field
    elif ( (2**(Config.WORDSIZE*8) - 0xffff) < val): # check signed int
      field = Field(structure, offset, FieldType.SIGNED_SMALLINT, Config.WORDSIZE, False)
      field.value = val
      field.endianess = endianess
      return field
    return None





class DSASimple(StructureAnalyser):
  ''' Simple structure analyzer that leverage simple type recognition heuristics.
  For all aligned offset, try to apply the following heuristics :
  ZeroFields: if the word is null
  UTF16Fields: if the offset contains utf-16 data
  PrintableAsciiFields: if the offset starts a printable ascii string
  IntegerFields: if the word value is small ( |x| < 65535 )
  PointerFields: if the word if a possible pointer value
  
  If the word content does not match theses heuristics, tag the fiel has unknown.
  '''
  zero_a = ZeroFields()
  ascii_a = PrintableAsciiFields()
  utf16_a = UTF16Fields()
  int_a = IntegerFields()
  ptr_a = PointerFields()

  def analyze_fields(self, structure):
    structure.reset()
    fields, gaps = self._analyze(structure)
    structure.add_fields(fields)
    structure.add_fields(gaps) #, FieldType.UNKNOWN
    structure.set_resolved()
    return structure
    
  def _analyze(self, structure):
    slen = len(structure)
    offset = 0
    # call on analyzers
    fields = []
    nb = -1
    gaps = [Field( structure, 0, FieldType.UNKNOWN, len(structure), False)]
    
    # find zeroes
    # find strings
    # find smallints
    # find pointers
    for analyser in [ self.zero_a, self.utf16_a, self.ascii_a, self.int_a, self.ptr_a]:
      for field in gaps:
        if field.padding:
          fields.append(field)
          continue
        log.debug('Using %s on %d:%d'%(analyser.__class__.__name__, field.offset, field.offset+len(field)))
        fields.extend( analyser.make_fields(structure, field.offset, len(field)) )
        #for f1 in fields:
        #  log.debug('after %s'%f1)
        #print fields
      if len(fields) != nb: # no change in fields, keep gaps
        nb = len(fields)
        gaps = self._make_gaps(structure, fields)
      if len(gaps) == 0:
        return fields, gaps
    return fields, gaps

  def _make_gaps(self, structure, fields):
    fields.sort()
    gaps = []
    nextoffset = 0
    for i, f in enumerate(fields):
      if f.offset > nextoffset : # add temp padding field
        self._aligned_gaps(structure, f.offset, nextoffset, gaps)
      elif f.offset < nextoffset :
        #log.debug(structure)
        #log.debug(f)
        #log.debug('%s < %s '%(f.offset, nextoffset) )
        #for f1 in fields:
        #  log.debug(f1)
        assert(False) # f.offset < nextoffset # No overlaps authorised
      # do next field
      nextoffset = f.offset + len(f)
    # conclude on QUEUE insertion
    lastfield_size = len(structure)-nextoffset
    if lastfield_size > 0 :
      if lastfield_size < Config.WORDSIZE:
        gap = Field( structure, nextoffset, FieldType.UNKNOWN, lastfield_size, True)
        log.debug('_make_gaps: adding last field at offset %d:%d'%(gap.offset, gap.offset+len(gap) ))
        gaps.append(gap)
      else:
        self._aligned_gaps(structure, len(structure), nextoffset, gaps)
    return gaps
  
  def _aligned_gaps(self, structure, endoffset, nextoffset, gaps):
    ''' if nextoffset is aligned
          add a gap to gaps, or 
        if nextoffset is not aligned
          add (padding + gap) to gaps 
         '''
    if nextoffset%Config.WORDSIZE == 0:
      gap = Field( structure, nextoffset, FieldType.UNKNOWN, endoffset-nextoffset, False)
      log.debug('_make_gaps: adding field at offset %d:%d'%(gap.offset, gap.offset+len(gap) ))
      gaps.append(gap)
    else:   # unaligned field should be splitted
      s1 = Config.WORDSIZE - nextoffset%Config.WORDSIZE
      gap1 = Field( structure, nextoffset, FieldType.UNKNOWN, s1, True)
      gap2 = Field( structure, nextoffset+s1, FieldType.UNKNOWN, endoffset-nextoffset-s1, False)
      log.debug('_make_gaps: Unaligned field at offset %d:%d'%(gap1.offset, gap1.offset+len(gap1) ))
      log.debug('_make_gaps: adding field at offset %d:%d'%(gap2.offset, gap2.offset+len(gap2) ))
      gaps.append(gap1)
      gaps.append(gap2)
    return


class EnrichedPointerFields(StructureAnalyser):
  ''' For all pointer fields in a structure, 
  try to enrich the field name with information about the child structure.
  
  All structure should have been Analysed, otherwise, 
  results are not going to be untertaining.
  '''
  
  def analyze_fields(self, structure):
    ''' @returns structure, with enriched info on pointer fields.
    For pointer fields value:
    (-) if pointer value is in mappings ( well it is... otherwise it would not be a pointer.)
    + if value is unaligned, mark it as cheesy
    + ask mappings for the context for that value
      - if context covers a data lib, it would give function names, .data , .text ( CodeContext )
      - if context covers a HEAP/heap extension (one context for multiple mmap possible) it would give structures
    + ask context for the target structure or code info
      - if retobj is structure, enrich pointer with info
    '''
    ## If you want to cache resolved infos, it still should be decided by the caller
    pointerFields = structure.getPointerFields()
    mappings = structure._context.mappings
    log.debug('got %d pointerfields'%(len(pointerFields)))
    for field in pointerFields:      
      value = field.value
      field.set_child_addr(value) # default
      ## FIXME field.set_resolved() # What ?
      # + if value is unaligned, mark it as cheesy
      if value%Config.WORDSIZE:
        field.set_uncertainty('Unaligned pointer value')
      # + ask mappings for the context for that value
      try:
        ctx = mappings.get_context(value) # no error expected.
        #log.warning('value: 0x%0.8x ctx.heap: 0x%0.8x'%(value, ctx.heap.start))
        #print '** ST id', id(structure), hex(structure._vaddr)
        # + ask context for the target structure or code info
      except ValueError,e:
        log.debug('target to non heap mmaps is not implemented')
        m = mappings.getMmapForAddr(value)
        field.set_child_desc('ext_lib @%0.8x %s'%(m.start, m.pathname))
        field._ptr_to_ext_lib = True
        field.set_child_ctype('void') # TODO: Function pointer ?
        field.set_name('ptr_ext_lib_%d'%(field.offset))
        continue
      tgt = None
      try:
        tgt = ctx.getStructureForOffset(value) # get enclosing structure @throws KeyError
      except (IndexError,ValueError), e: # there is no child structure member at pointed value.
        log.debug('there is no child structure enclosing pointed value %0.8x - %s'%(value, e))
        field.set_child_desc('Memory management space')
        field.set_child_ctype('void') 
        field.set_name('ptr_void')
        continue
      # structure found
      field.set_child_addr(tgt._vaddr) # we always point on structure, not field
      offset = value - tgt._vaddr
      try:
        tgt_field = tgt.get_field_at_offset(offset) # @throws IndexError
      except IndexError, e: # there is no field right there
        log.debug('there is no field at pointed value %0.8x. May need splitting byte field - %s'%(value, e))
        field.set_child_desc('Badly reversed field')
        field.set_child_ctype('void') 
        field.set_name('ptr_void')
        continue
      # do not put exception for field 0. structure name should appears anyway.
      field.set_child_desc('%s.%s'%(tgt.get_name(), tgt_field.get_name()) )
      # TODO:
      # do not complexify code by handling target field type,
      # lets start with simple structure type pointer,
      # later we would need to use tgt_field.ctypes depending on field offset
      field.set_child_ctype(tgt.get_name())        
      field.set_name('%s_%s'%(tgt.get_name(), tgt_field.get_name()) )
      # all
    return
  
  def get_unresolved_children(self, structure):
    ''' returns all children that are not fully analyzed yet.'''
    pointerFields = structure.getPointerFields()
    children = []
    for field in pointerFields:
      try:
        tgt = structure._context.getStructureForAddr(field.value)
        if not tgt.is_resolved(): # fields have not been decoded yet
          children.append(tgt)
      except KeyError,e:
        pass
    return children        



class IntegerArrayFields(StructureAnalyser):
  ''' TODO '''
  def make_fields(self, structure, offset, size):
    # this should be last resort
    bytes = self.struct.bytes[self.offset:self.offset+self.size]
    size = len(bytes)
    if size < 4:
      return False
    ctr = collections.Counter([ bytes[i:i+Config.WORDSIZE] for i in range(len(bytes)) ] )
    floor = max(1,int(size*.1)) # 10 % variation in values
    #commons = [ c for c,nb in ctr.most_common() if nb > 2 ]
    commons = ctr.most_common()
    if len(commons) > floor:
      return False # too many different values
    # few values. it migth be an array
    self.size = size
    self.values = bytes
    self.comment = '10%% var in values: %s'%(','.join([ repr(v) for v,nb in commons]))
    return True
        
    

