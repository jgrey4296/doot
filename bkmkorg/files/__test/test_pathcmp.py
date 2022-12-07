#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
import unittest
import warnings
from importlib.resources import files
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
from unittest import mock

from bkmkorg.files.pathcmp import PathCmp
##-- end imports

##-- warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    pass
##-- end warnings

##-- data
data_path = files("bkmkorg.files.__test")
left = data_path / "left"
right = data_path / "right"
##-- end data

class TestPathCmp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        LOGLEVEL      = logmod.DEBUG
        LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)

        cls.file_h        = logmod.FileHandler(LOG_FILE_NAME, mode="w")
        cls.file_h.setLevel(LOGLEVEL)

        logging = logmod.getLogger(__name__)
        logging.root.addHandler(cls.file_h)
        logging.root.setLevel(logmod.NOTSET)


    @classmethod
    def tearDownClass(cls):
        logmod.root.removeHandler(cls.file_h)

    def test_initial(self):
        testobj = PathCmp(left, right)

        self.assertIsNotNone(testobj)

    def test_phase0(self):
        testobj = PathCmp(left, right)

        self.assertFalse(testobj.left_list)
        self.assertFalse(testobj.right_list)

        testobj.phase0()

        self.assertTrue(testobj.left_list)
        self.assertTrue(testobj.right_list)

        self.assertIn(left/"test_file.test", testobj.left_list)
        self.assertIn(right/"test_file.test", testobj.right_list)

    def test_phase1(self):
        testobj = PathCmp(left, right)

        self.assertFalse(testobj.common)
        self.assertFalse(testobj.left_only)
        self.assertFalse(testobj.right_only)

        testobj.phase0()
        testobj.phase1()

        self.assertTrue(testobj.common)
        self.assertTrue(testobj.left_only)
        self.assertTrue(testobj.right_only)

        self.assertIn(left/"left_only.test", testobj.left_only)
        self.assertIn(right/"right_only.test", testobj.right_only)

        self.assertNotIn(right/"left_only.test", testobj.right_only)
        self.assertNotIn(left/"right_only.test", testobj.left_only)

        self.assertIn("common", testobj.common)
        self.assertIn("one_down", testobj.common)


    def test_phase2(self):
        testobj = PathCmp(left, right)

        self.assertFalse(testobj.common_dirs)
        self.assertFalse(testobj.common_files)
        self.assertFalse(testobj.common_funny)

        testobj.phase0()
        testobj.phase1()
        testobj.phase2()

        self.assertTrue(testobj.common_dirs)
        self.assertTrue(testobj.common_files)
        self.assertTrue(testobj.common_funny)

        self.assertIn("one_down" , testobj.common_dirs)
        self.assertIn("common"   , testobj.common_files)
        self.assertIn("funny"    , testobj.common_funny)



if __name__ == '__main__':
    unittest.main()
