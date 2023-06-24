#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import logging as logmod
import unittest
import warnings
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
from unittest import mock
##-- end imports
logging = logmod.root

##-- warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    pass
##-- end warnings

import sys
import tomler
import doot
doot.config = tomler.Tomler({})
from doot.control.overlord import DootOverlord

class TestOverlord(unittest.TestCase):
    ##-- setup-teardown
    @classmethod
    def setUpClass(cls):
        LOGLEVEL      = logmod.DEBUG
        LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)

        cls.file_h        = logmod.FileHandler(LOG_FILE_NAME, mode="w")
        cls.file_h.setLevel(LOGLEVEL)

        logging.setLevel(logmod.NOTSET)
        logging.addHandler(cls.file_h)


    @classmethod
    def tearDownClass(cls):
        logging.removeHandler(cls.file_h)

    ##-- end setup-teardown

    @mock.patch.object(sys, "argv", ["doot"])
    def test_initial(self):
        overlord = DootOverlord()
        self.assertIsNotNone(overlord)
        self.assertEqual(overlord.args, ["doot"])



    @mock.patch.object(sys, "argv", ["doot"])
    def test_plugins_loaded(self):
        overlord = DootOverlord()
        self.assertTrue(overlord.plugins)
        self.assertTrue(all(x in overlord.plugins for x in doot.constants.default_plugins.keys()))

    @mock.patch.object(sys, "argv", ["doot"])
    def test_cmds_loaded(self):
        overlord = DootOverlord()
        self.assertTrue(overlord.cmds)
        self.assertEqual(len(overlord.cmds), len(doot.constants.default_plugins['command']))


    @mock.patch.object(sys, "argv", ["doot"])
    def test_taskers_loaded(self):
        overlord = DootOverlord(
            extra_config={"tasks" : {"basic" : [{"name": "simple", "type": "basic"}]}}
        )
        self.assertTrue(overlord.taskers)


    @mock.patch.object(sys, "argv", ["doot"])
    def test_taskers_multi(self):
        overlord = DootOverlord(extra_config={
            "tasks" : {"basic": [
                {"name": "simple", "type": "basic"},
                {"name": "another", "type": "basic"}
        ]}})
        self.assertTrue(overlord.taskers)
        self.assertEqual(len(overlord.taskers), 2)


    @mock.patch.object(sys, "argv", ["doot"])
    def test_taskers_name_conflict(self):
        with self.assertRaises(ResourceWarning):
            DootOverlord(extra_config={
                "tasks" : {"basic" : [
                    {"name": "simple", "type": "basic"},
                    {"name": "simple", "type": "basic"}
            ]}})

    @mock.patch.object(sys, "argv", ["doot"])
    def test_taskers_bad_type(self):
        with self.assertRaises(ResourceWarning):
            DootOverlord(extra_config={"tasks" : {"basic": [{"name": "simple", "type": "not_basic"}]}})


##-- ifmain
if __name__ == '__main__':
    unittest.main()
##-- end ifmain
