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

import importlib.metadata
import tomler
import doot
doot.config = tomler.Tomler({})
from doot.loaders import task_loader
logging = logmod.root

##-- warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    pass
##-- end warnings

class TestTaskLoader(unittest.TestCase):
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
        basic = task_loader.DootTaskLoader()
        self.assertTrue(basic)

    def test_basic__internal_load(self):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DootTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({})
        result = basic._load_raw_specs(tomler.Tomler(specs).tasks)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], "test")

    def test_basic__load(self):
        specs = {"tasks": {"basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DootTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)
        result = basic.load()

        self.assertIsInstance(result, tomler.Tomler)
        self.assertEqual(len(result), 1)
        self.assertIn("test", result)
        self.assertIsInstance(result['test'][0], dict)
        self.assertIsInstance(result['test'][1], type)


    def test_multi_load(self):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DootTasker"})
        specs['tasks']['basic'].append({"name"  : "other", "class": "doot.task.base_tasker::DootTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)
        result = basic.load()

        self.assertIsInstance(result, tomler.Tomler)
        self.assertEqual(len(result), 2)
        self.assertIn("test", result)
        self.assertIn("other", result)

    def test_name_disallow_overload(self):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DootTasker"})
        specs['tasks']['basic'].append({"name"  : "test", "class": "doot.task.base_tasker::DootTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)
        task_loader.allow_overloads = False

        with self.assertRaises(ResourceWarning):
            basic.load()

    def test_name_allow_overload(self):
        specs = {"tasks": { "basic": []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DootTasker"})
        specs['tasks']['basic'].append({"name"  : "test", "class": "doot.task.base_tasker::DootTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, tomler.Tomler(specs))
        task_loader.allow_overloads = True

        result = basic.load()
        self.assertIn("test", result)

    def test_cmd_name_conflict(self):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DootTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)
        basic.cmd_names = set(["test"])

        with self.assertRaises(ResourceWarning):
            basic.load()


    def test_bad_task_class(self):
        specs = {"tasks": { "basic": []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DoesntExistTasker"})

        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)

        with self.assertRaises(ResourceWarning):
            basic.load()

    def test_bad_task_module(self):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.doesnt_exist_module::DoesntExistTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)

        with self.assertRaises(ResourceWarning):
            basic.load()


    def test_bad_spec(self):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)

        with self.assertRaises(ResourceWarning):
            result = basic.load()

    @mock.patch("importlib.metadata.EntryPoint")
    def test_task_type(self, mock_class):
        specs = {"tasks": {"basic": []}}
        specs['tasks']['basic'].append({"name": "simple", "type": "basic"})

        mock_ep      = importlib.metadata.EntryPoint()
        mock_ep.name = "basic"
        mock_ep.load = mock.MagicMock(return_value=True)

        plugins      = tomler.Tomler({"task": [mock_ep]})
        basic        = task_loader.DootTaskLoader()
        basic.setup(plugins, tomler.Tomler(specs))

        result = basic.load()
        self.assertEqual(len(result), 1)
        self.assertEqual(result.simple, ({"name": "simple", "type": "basic", "group": "basic"}, True))

    @mock.patch("importlib.metadata.EntryPoint")
    def test_task_bad_type(self, mock_class):
        specs = {"tasks": {"basic": []}}
        specs['tasks']['basic'].append({"name": "simple", "type": "not_basic"})

        mock_ep      = importlib.metadata.EntryPoint()
        mock_ep.name = "basic"
        mock_ep.load = mock.MagicMock(return_value=True)

        plugins      = tomler.Tomler({"task": [mock_ep]})
        basic        = task_loader.DootTaskLoader()
        basic.setup(plugins, tomler.Tomler(specs))

        with self.assertRaises(ResourceWarning):
            basic.load()

##-- ifmain
if __name__ == '__main__':
    unittest.main()
##-- end ifmain
