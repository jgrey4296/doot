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

from doot.parsers.parser import DootArgParser
from doot._abstract.parser import DootParamSpec

class TestParamSpec(unittest.TestCase):
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

    def test_paramspec(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        self.assertIsInstance(example, DootParamSpec)

    def test_equal(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        self.assertEqual(example, "test")
        self.assertEqual(example, "test=blah")
        self.assertEqual(example, "-test")
        self.assertEqual(example, "-test=blah")
        self.assertEqual(example, "-t")
        self.assertEqual(example, "-t=blah")

    def test_equal_fail(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        self.assertNotEqual(example, "atest")
        self.assertNotEqual(example, "--test")
        self.assertNotEqual(example, "-tw")

    def test_add_value_bool(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        self.assertEqual(example, "test")
        data = {}
        example.add_value(data, "test")
        self.assertIn('test', data)
        self.assertTrue(data['test'])

    def test_add_value_short_bool(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        self.assertEqual(example, "test")
        data = {}
        example.add_value(data, "-t")
        self.assertIn('test', data)
        self.assertTrue(data['test'])

    def test_add_value_short_bool(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        self.assertEqual(example, "test")
        data = {}
        with self.assertRaises(TypeError):
            example.add_value(data, "-t=blah")

    def test_add_value_inverse_bool(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        self.assertEqual(example, "test")
        data = {}
        example.add_value(data, "-no-test")
        self.assertIn('test', data)
        self.assertFalse(data['test'])

    def test_add_value_list(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [],
          })
        self.assertEqual(example, "test")
        data = {'test': []}
        example.add_value(data, "-test=bloo")
        self.assertIn('test', data)
        self.assertEqual(data['test'], ["bloo"])

    def test_add_value_list_multi(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [],
          })
        self.assertEqual(example, "test")
        data = {'test': []}
        example.add_value(data, "-test=bloo")
        example.add_value(data, "-test=blah")
        self.assertIn('test', data)
        self.assertEqual(data['test'], ["bloo", "blah"])

    def test_add_value_list_multi_joined(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [],
          })
        self.assertEqual(example, "test")
        data = {'test': []}
        example.add_value(data, "-test=bloo,blah")
        self.assertIn('test', data)
        self.assertEqual(data['test'], ["bloo", "blah"])

    def test_add_value_set_multi_joined(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : set,
            "default" : set(),
          })
        self.assertEqual(example, "test")
        data = {'test': set()}
        example.add_value(data, "-test=bloo,blah")
        self.assertIn('test', data)
        self.assertEqual(data['test'], {"bloo", "blah"})

    def test_add_value_set_missing_joined(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : set,
            "default" : set(),
          })
        self.assertEqual(example, "test")
        data = {} # <---
        example.add_value(data, "-test=bloo,blah")
        self.assertIn('test', data)
        self.assertEqual(data['test'], {"bloo", "blah"})

    def test_add_value_str(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : str,
            "default" : "",
          })
        self.assertEqual(example, "test")
        data = {} # <---
        example.add_value(data, "-test=bloo,blah")
        self.assertIn('test', data)
        self.assertEqual(data['test'], "bloo,blah")

    def test_add_value_str_multi_set_fail(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : str,
            "default" : "",
          })
        self.assertEqual(example, "test")
        data = {} # <---
        example.add_value(data, "-test=bloo,blah")
        with self.assertRaises(Exception):
            example.add_value(data, "-test=aweg")

    def test_add_value_custom_value(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : lambda x: int(x) + 2,
            "default" : 5,
          })
        self.assertEqual(example, "test")
        data = {} # <---
        example.add_value(data, "-test=2")
        self.assertEqual(example, "test")
        self.assertEqual(data['test'], 4)


class TestArgParser(unittest.TestCase):
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
        parser = DootArgParser()
        parsed = parser.parse([
            "doot", "-v", "2", "blah"
                               ],
            [], {}, {})

        name = parsed.on_fail(False).head.name()
        self.assertEqual(name, "doot")

    def test_cmd(self):
        cmd_mock = mock.MagicMock()
        parser   = DootArgParser()
        result   = parser.parse([
            "doot", "list"
                               ],
            [], {"list": cmd_mock}, {}
            )

        self.assertEqual(result.on_fail(False).head.name(), "doot")
        self.assertEqual(result.on_fail(False).cmd.name(), "list")

    def test_cmd_args(self):
        cmd_mock            = mock.MagicMock()
        type(cmd_mock).param_specs = mock.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])

        parser = DootArgParser()
        result = parser.parse([
            "doot", "list", "-all"
                               ],
            [], {"list": cmd_mock}, {}
            )
        self.assertEqual(result.on_fail(False).head.name(), "doot")
        self.assertEqual(result.on_fail(False).cmd.name(), "list")
        self.assertEqual(result.on_fail(False).cmd.args.all(), True)

    def test_cmd_arg_fail(self):
        cmd_mock            = mock.MagicMock()
        type(cmd_mock).param_specs = mock.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])

        parser = DootArgParser()
        with self.assertRaises(Exception):
            parser.parse([
                "doot", "list", "-all", "-bloo"
            ],
            [], {"list": cmd_mock}, {}
        )


    def test_cmd_then_task(self):
        cmd_mock            = mock.MagicMock()
        type(cmd_mock).param_specs = mock.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])
        task_mock            = mock.MagicMock()
        type(task_mock).param_specs = mock.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])

        parser = DootArgParser()
        result = parser.parse([
            "doot", "list", "blah"
                               ],
            [], {"list": cmd_mock}, {"blah": task_mock},
            )
        self.assertEqual(result.on_fail(False).head.name(), "doot")
        self.assertEqual(result.on_fail(False).cmd.name(), "list")
        self.assertTrue(result.on_fail(False).tasks.blah())

    def test_cmd_then_complex_task(self):
        cmd_mock            = mock.MagicMock()
        type(cmd_mock).param_specs = mock.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])
        task_mock            = mock.MagicMock()
        type(task_mock).param_specs = mock.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])

        parser = DootArgParser()
        result = parser.parse([
            "doot", "list", "blah::bloo.blee"
                               ],
            [], {"list": cmd_mock}, {"blah::bloo.blee": task_mock},
            )
        self.assertEqual(result.on_fail(False).head.name(), "doot")
        self.assertEqual(result.on_fail(False).cmd.name(), "list")
        self.assertTrue(result.on_fail(False).tasks["blah::bloo.blee"]())

    def test_task_args(self):
        cmd_mock            = mock.MagicMock()
        type(cmd_mock).param_specs = mock.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])
        type(cmd_mock).name = mock.PropertyMock(return_value="list")

        parser = DootArgParser()
        result = parser.parse([
            "doot", "list", "-all"
                               ],
            [], {}, {"list": cmd_mock}
            )
        self.assertEqual(result.on_fail(False).head.name(), "doot")
        self.assertEqual(result.on_fail(False).cmd.name(), "run")
        self.assertTrue(result.on_fail(False).tasks.list())
        self.assertEqual(result.on_fail(False).tasks.list.all(), True)

    def test_task_args_default(self):
        cmd_mock            = mock.MagicMock()
        type(cmd_mock).param_specs = mock.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])
        type(cmd_mock).name = mock.PropertyMock(return_value="list")

        parser = DootArgParser()
        result = parser.parse([
            "doot", "list", # no "-all"
                               ],
            [], {}, {"list": cmd_mock}
            )
        self.assertEqual(result.on_fail(False).head.name(), "doot")
        self.assertTrue(result.on_fail(False).tasks.list())
        self.assertEqual(result.on_fail(False).tasks.list.all(), False)

    def test_tasks_dup_fail(self):
        cmd_mock            = mock.MagicMock()
        type(cmd_mock).param_specs = mock.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])
        type(cmd_mock).name = mock.PropertyMock(return_value="list")

        parser = DootArgParser()
        with self.assertRaises(Exception):
            parser.parse([
                "doot", "list", "-all", "list"
                         ],
                [], {}, {"list": cmd_mock}
            )



##-- ifmain
if __name__ == '__main__':
    unittest.main()
##-- end ifmain
