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

import tomler
import doot
doot.config = tomler.Tomler({})
from doot.loaders import plugin_loader
logging = logmod.root

##-- warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    pass
##-- end warnings

class TestPluginLoader(unittest.TestCase):
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

    def test_initial(self):
        basic = plugin_loader.DootPluginLoader()
        self.assertTrue(basic)

##-- ifmain
if __name__ == '__main__':
    unittest.main()
##-- end ifmain
