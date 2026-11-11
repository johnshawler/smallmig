#!/usr/bin/env python3
"""Bounds/ownership preflight tests; no ROM or compiler required."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_check import renderer_storage
class StorageMetadata(unittest.TestCase):
    def setUp(self):
        self.game={'hwmem':0x1000,'_chip_start':0x1000,'_chip_end':0x100000,
                   'ar_hw_setmem':0x210000,'_load_end':0x280000}
        self.sizes={'hwmem':970780}
    def test_valid(self):
        self.assertEqual(renderer_storage(self.game,self.sizes),[0x210000,0x1000,970780])
    def test_invalid_addresses(self):
        for key,value in [('hwmem',0),('hwmem',0x1001),('hwmem',0x100000),
                          ('_chip_start',0),('_chip_end',0x200001),
                          ('ar_hw_setmem',0),('ar_hw_setmem',0x280000)]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                renderer_storage({**self.game,key:value},self.sizes)
    def test_invalid_sizes(self):
        for size in (0,4,7,970781,0x100000):
            with self.subTest(size=size),self.assertRaises(ValueError):
                renderer_storage(self.game,{'hwmem':size})
if __name__=='__main__':unittest.main()
