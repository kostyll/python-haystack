#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for haystack.reverse.structure."""

import logging
import struct
import operator
import os
import unittest
import pickle
import sys

from haystack.config import Config
from haystack.reverse.win32 import ctypes_malloc
from haystack.reverse import reversers

__author__ = "Loic Jaquemet"
__copyright__ = "Copyright (C) 2012 Loic Jaquemet"
__license__ = "GPL"
__maintainer__ = "Loic Jaquemet"
__email__ = "loic.jaquemet+python@gmail.com"
__status__ = "Production"

import ctypes 

class TestAllocator(unittest.TestCase):

  def setUp(self):  
    self.context = reversers.getContext('test/dumps/putty/putty.1.dump')

  def test_search(self):
    ''' def search(mappings, heap, filterInuse=False ):'''
    self.skipTest('notready')
    return  

  def test_getUserAllocations(self):
    ''' def getUserAllocations(mappings, heap, filterInuse=False):'''
    self.skipTest('notready')
    return  

  def test_isMallocHeap(self):
    ''' def isMallocHeap(mappings, mapping):'''
    self.skipTest('notready')
    return  


if __name__ == '__main__':
  unittest.main(verbosity=0)
  #suite = unittest.TestLoader().loadTestsFromTestCase(TestFunctions)
  #unittest.TextTestRunner(verbosity=2).run(suite)