#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Loic Jaquemet loic.jaquemet+python@gmail.com
#

'''
This module holds some basic constraint class for the Haystack model.
Several useful function validation are also here, like pointer validation.

'''

__author__ = "Loic Jaquemet loic.jaquemet+python@gmail.com"


import ctypes
import os
import struct
from struct import pack
from struct import unpack 

import logging

from haystack.config import Config

log = logging.getLogger('utils')

def formatAddress(addr): 
  if Config.WORDSIZE == 4:
    return u"0x%08x" % addr
  else:
    return u"0x%016x" % addr

def unpackWord(bytes, endianess='@'):
  if Config.WORDSIZE == 8:
    return struct.unpack('%sQ'%endianess, bytes)[0]
  else:
    return struct.unpack('%sI'%endianess, bytes)[0]

def is_valid_address(obj, mappings, structType=None):
  ''' 
  :param obj: the obj to evaluate.
  :param mappings: the memory mappings in a list.
  :param structType: the object's type, so the size could be taken in consideration.
  
  Returns False if the object address is NULL.
  Returns False if the object address is not in a mapping.
  Returns False if the object overflows the mapping.
  
  Returns the mapping in which the object stands otherwise.
  '''
  # check for null pointers
  addr = getaddress(obj)
  if addr == 0:
    return False
  return is_valid_address_value(addr, mappings, structType)

def is_valid_address_value(addr, mappings, structType=None):
  ''' 
  :param addr: the address to evaluate.
  :param mappings: the memory mappings in a list.
  :param structType: the object's type, so the size could be taken in consideration.
  
  Returns False if the object address is NULL.
  Returns False if the object address is not in a mapping.
  Returns False if the object overflows the mapping.
  
  Returns the mapping in which the address stands otherwise.
  '''
  m = mappings.getMmapForAddr(addr)
  log.debug( 'is_valid_address_value = %x %s'%( addr, m ))
  if m:
    if (structType is not None):
      s = ctypes.sizeof(structType)
      if (addr+s) < m.start or (addr+s) > m.end:
        return False
    return m
  return False

def is_address_local(obj, structType=None):
  ''' 
  Costly , checks if obj is mapped to local memory space.

  Returns the memory mapping if found.
    False, otherwise.
  '''
  addr=getaddress(obj)
  if addr == 0:
    return False
  class P:
    pid=os.getpid()
  from memory_mapping import readProcessMappings  # loading dependencies
  mappings = readProcessMappings(P()) # memory_mapping
  return is_valid_address(obj, mappings, structType)

def getaddress(obj):
  ''' 
  Returns the address of the struct pointed by the obj, or null if invalid.

  :param obj: a pointer.
  '''
  # check for null pointers
  if hasattr(obj,'_sub_addr_'):
    #print 'obj._sub_addr_', hex(obj._sub_addr_)
    return obj._sub_addr_
  if bool(obj):
    if not hasattr(obj,'contents'):
      return 0
    #print '** NOT MY HAYSTACK POINTER'
    return ctypes.addressof(obj.contents)
  else:
    return 0  

def container_of(memberaddr, typ, membername):
  '''
  Returns the instance of typ(), in which the member "membername' is really.
  
  :param memberadd: the address of membername.
  :param typ: the type of the containing structure.
  :param membername: the membername.
  
  Stolen from linux kernel headers.
         const typeof( ((typ *)0)->member ) *__mptr = (ptr);    
        (type *)( (char *)__mptr - offsetof(type,member) );}) 
  '''
  return typ.from_address( memberaddr - offsetof(typ, membername) )

def offsetof(typ, membername):
  '''
  Returns the offset of a member in a structure.
  
  :param typ: the structure type.
  :param membername: the membername in that structure.
  '''
  #T=typ()
  #return ctypes.addressof(  getattr(T,membername) ) - ctypes.addressof(T)
  return getattr(typ, membername).offset


''' MISSING
d 	double 	float 	8 	(4)
p 	char[] 	string 	  	 
'''
# TODO DELETE ans use obj._type_
bytestr_fmt={ # XXX probable bug here on x64...
  'c_bool': '?',
  'c_char': 'c',
  'c_byte': 'b',
  'c_ubyte': 'B',
  'c_short': 'h',
  'c_ushort': 'H',
  'c_int': 'i', #c_int is c_long
  'c_uint': 'I',
  'int': 'i', 
  'c_long': 'l', #c_int is c_long
  'c_ulong': 'L',
  'long': 'q', 
  'c_longlong': 'q',
  'c_ulonglong': 'Q',
  'c_float': 'f', ## and double float ?
  'c_char_p': 's',
  'c_void_p': 'P',
  'c_void': 'P', ## void in array is void_p ##DEBUG
  }

def array2bytes_(array, typ):
  ''' Convert an array of typ() to a byte string.'''
  arrayLen = len(array)
  if arrayLen == 0:
    return b''
  if typ not in bytestr_fmt:
    log.warning('Unknown ctypes to pack: %s %s'%(typ,array))
    return None
  if typ  == 'c_void':
    return b'' # void array cant be extracted
  fmt = bytestr_fmt[typ]
  # TODO fmt = typ._type_
  sb=b''
  try:
    for el in array:
      sb+=pack(fmt, el)
  except Exception ,e:
    log.warning('%s %s'%(fmt,el))
    #raise e
  return sb

def array2bytes(array):
  ''' Convert an array of undetermined Basic Ctypes class to a byte string, 
  by guessing it's type from it's class name.
  
  This is a bad example of introspection.
  '''
  if not isBasicTypeArray(array):
    return b'NOT-AN-BasicType-ARRAY'
  # BEURK
  #log.info(type(array).__name__.split('_'))
  #typ='_'.join(type(array).__name__.split('_')[:2])
  #return array2bytes_(array, array._type_)
  sb = b''
  for el in array:
    sb+=pack(array._type_._type_, el)
  return sb


def bytes2array(bytes, typ):
  ''' Converts a bytestring in a ctypes array of typ() elements.'''
  typLen=ctypes.sizeof(typ)
  if len(bytes)%typLen != 0:
    raise ValueError('thoses bytes are not an array of %s'%(typ))
  arrayLen=len(bytes)/typLen
  array=(typ*arrayLen)()
  if arrayLen == 0:
    return array
  if typ.__name__ not in bytestr_fmt:
    log.warning('Unknown ctypes to pack: %s'%(typ))
    return None
  fmt=bytestr_fmt[typ.__name__]
  sb=b''
  import struct
  try:
    for i in range(0,arrayLen):
      array[i]=struct.unpack(fmt, bytes[typLen*i:typLen*(i+1)])[0]
  except struct.error,e:
    log.error('format:%s typLen*i:typLen*(i+1) = %d:%d'%(fmt, typLen*i,typLen*(i+1)))
    raise e
  return array


def pointer2bytes(attr,nbElement):
  ''' 
  Returns an array from a ctypes POINTER, geiven the number of elements.
  
  :param attr: the structure member.
  :param nbElement: the number of element in the array.
  '''
  # attr is a pointer and we want to read elementSize of type(attr.contents))
  if not is_address_local(attr):
    return 'POINTER NOT LOCAL'
  firstElementAddr=getaddress(attr)
  array=(type(attr.contents)*nbElement).from_address(firstElementAddr)
  # we have an array type starting at attr.contents[0]
  return array2bytes(array)

def isCTypes(obj):
  ''' Checks if an object is a ctypes type object'''
  return  issubclass(type(obj), ctypes.Structure) #or (type(obj).__module__ in ['ctypes','_ctypes']) 
    
def isBasicType(objtype):
  ''' Checks if an object is a ctypes basic type, or a python basic type.'''
  if not isinstance(objtype, type):  return False
  return (isinstance(objtype, type) and not isPointerType(objtype) and not isFunctionType(objtype) 
          and (objtype.__module__ in ['ctypes','_ctypes','__builtin__']) )
  #return not isPointerType(obj) and not isFunctionType(obj) and (type(obj).__module__ in ['ctypes','_ctypes','__builtin__']) 

def isStructType(objtype):
  ''' Checks if an object is a ctypes Structure.'''
  if not isinstance(objtype, type):  return False
  return issubclass(objtype, ctypes.Structure)

def isUnionType(objtype):
  ''' Checks if an object is a ctypes Union.'''
  if not isinstance(objtype, type):  return False
  return issubclass(objtype,ctypes.Union) and not isCStringPointer(objtype)

def isPointerType(objtype):
  ''' Checks if an object is a ctypes pointer.m CTypesPointer or CSimpleTypePointer'''
  if hasattr(objtype, '_subtype_'):
    return True
  if not isinstance(objtype, type):  return False
  return Config.PTR_TYPE == type(objtype) or isVoidPointerType(objtype) or isFunctionType(objtype)
  #return __ptrt == type(type(obj)) or type(type(obj)) == type(ctypes.c_void_p) or isFunctionType(obj)

def isPointerBasicType(objtype):
  ''' Checks if an object is a pointer to a BasicType'''
  if not isinstance(objtype, type):  return False
  if not hasattr(objtype, '_type_'):  
    return False
  return isBasicType(objtype._type_)

def isPointerStructType(objtype):
  ''' Checks if an object is a pointer to a Structure'''
  if not isinstance(objtype, type):  return False
  if hasattr(objtype, '_type_') and isStructType(objtype._type_):
    return True
  return False

def isPointerUnionType(objtype):
  ''' Checks if an object is a pointer to a Union'''
  if not isinstance(objtype, type):  return False
  return hasattr(objtype, '_type_') and isUnionType(objtype._type_)

def isVoidPointerType(objtype):
  ''' Checks if an object is a ctypes pointer.m CTypesPointer or CSimpleTypePointer'''
  if hasattr(objtype, '_subtype_'):
    if objtype._subtype_ == type(None):
      return True 
  if not isinstance(objtype, type):  return False
  return objtype in [ctypes.original_c_char_p, ctypes.c_wchar_p, ctypes.c_void_p]

def isBasicTypeArray(obj):
  ''' Checks if an object is a array of basic types.
  It checks the type of the first element.
  The array should not be null :).
  '''
  if isArrayType(type(obj)):
    if len(obj) == 0:
      return False # no len is no BasicType
    if isPointerType(type(obj[0])):
      return False
    if isBasicType(type(obj[0])):
      return True
  return False

__arrayt = type(ctypes.c_byte*1)
def isArrayType(objtype):
  ''' Checks if an object is a ctype array.'''
  if not isinstance(objtype, type):  return False
  return __arrayt == type(objtype)

__cfuncptrt = type(type(ctypes.memmove))
def isFunctionType(objtype):
  ''' Checks if an object is a function pointer.'''
  if not isinstance(objtype, type):  return False
  return __cfuncptrt == type(objtype)

def isCStringPointer(objtype):
  ''' Checks if an object is our CString.'''
  #return isinstance(obj, haystack.model.CString) 
  #return obj.__class__.__name__ == 'CString'
  if not isinstance(objtype, type):  return False
  import haystack
  return issubclass(objtype, haystack.model.CString) 
  


class IgnoreMember:
  ''' 
  Constraint class for the Haystack model.
  If this constraints is applied on a Structure member, 
  the member will be ignored by the validation engine.
  '''
  def __contains__(self,obj):
    return True

class RangeValue:
  ''' 
  Constraint class for the Haystack model.
  If this constraints is applied on a Structure member, 
  the member has to be between 'low' and 'high' values to be
  considered as Valid.
  '''
  def __init__(self,low,high):
    self.low=low
    self.high=high
  def __contains__(self,obj):
    return self.low <= obj <= self.high
  def __eq__(self,obj):
    return self.low <= obj <= self.high

class NotNullComparable:
  ''' 
  Constraint class for the Haystack model.
  If this constraints is applied on a Structure member, 
  the member should not be null to be considered valid by the validation engine.
  '''
  def __contains__(self,obj):
    return bool(obj)
  def __eq__(self,obj):
    return bool(obj)

''' 
Constraint class for the Haystack model.
If this constraints is applied on a Structure member, 
the member should not be null to be considered valid by the validation engine.
'''
NotNull=NotNullComparable()


class BytesComparable:
  ''' 
  Constraint class for the Haystack model.
  If this constraints is applied on a Structure member, 
  the member should have the same bytes value and length.
  '''
  def __init__(self, seq):
    self.seq = seq

  def __contains__(self,obj):
    if cmp(self,obj) == 0:
      return True
    return False

  def __cmp__(self,obj):
    if isinstance(obj, type(ctypes.c_void_p)):
      if ctypes.sizeof(obj) != len(seq):
        return -1
      bytes = ctypes.string_at(ctypes.addressof(obj), ctypes.sizeof(obj) )
      if bytes == self.seq:
        return 0
      else:
        return -1
    return cmp(self.seq, ctypes.string_at(ctypes.addressof(obj), ctypes.sizeof(obj) ) )

PerfectMatch=BytesComparable


py_xrange=xrange
def xrange(start, end, step=1):
  ''' stoupid xrange can't handle long ints... '''
  end=end-start
  for val in py_xrange(0, end, step):
    yield start+val
  return


