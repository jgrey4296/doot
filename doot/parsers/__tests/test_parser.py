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

import pytest
from doot.parsers.parser import DootArgParser
from doot._abstract.parser import DootParamSpec

class TestParamSpec(unittest.TestCase):

    def test_paramspec(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(isinstance(example, DootParamSpec))

    def test_equal(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(example == "test")
        assert(example == "test=blah")
        assert(example == "-test")
        assert(example == "-test=blah")
        assert(example == "-t")
        assert(example == "-t=blah")

    def test_equal_fail(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(example != "atest")
        assert(example != "--test")
        assert(example != "-tw")

    def test_add_value_bool(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(example == "test")
        data = {}
        example.add_value(data, "test")
        assert('test' in data)
        assert(bool(data['test']))

    def test_add_value_short_bool(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(example == "test")
        data = {}
        example.add_value(data, "-t")
        assert('test' in data)
        assert(bool(data['test']))

    def test_add_value_short_bool(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(example == "test")
        data = {}
        with pytest.raises(TypeError):
            example.add_value(data, "-t=blah")

    def test_add_value_inverse_bool(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(example == "test")
        data = {}
        example.add_value(data, "-no-test")
        assert('test' in data)
        assert(not bool(data['test']))

    def test_add_value_list(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [],
          })
        assert(example == "test")
        data = {'test': []}
        example.add_value(data, "-test=bloo")
        assert('test' in data)
        assert(data['test'] == ["bloo"])

    def test_add_value_list_multi(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [],
          })
        assert(example == "test")
        data = {'test': []}
        example.add_value(data, "-test=bloo")
        example.add_value(data, "-test=blah")
        assert('test' in data)
        assert(data['test'] == ["bloo", "blah"])

    def test_add_value_list_multi_joined(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [],
          })
        assert(example == "test")
        data = {'test': []}
        example.add_value(data, "-test=bloo,blah")
        assert('test' in data)
        assert(data['test'] == ["bloo", "blah"])

    def test_add_value_set_multi_joined(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : set,
            "default" : set(),
          })
        assert(example == "test")
        data = {'test': set()}
        example.add_value(data, "-test=bloo,blah")
        assert('test' in data)
        assert(data['test'] == {"bloo", "blah"})

    def test_add_value_set_missing_joined(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : set,
            "default" : set(),
          })
        assert(example == "test")
        data = {} # <---
        example.add_value(data, "-test=bloo,blah")
        assert('test' in data)
        assert(data['test'] == {"bloo", "blah"})

    def test_add_value_str(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : str,
            "default" : "",
          })
        assert(example == "test")
        data = {} # <---
        example.add_value(data, "-test=bloo,blah")
        assert('test' in data)
        assert(data['test'] == "bloo,blah")

    def test_add_value_str_multi_set_fail(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : str,
            "default" : "",
          })
        assert(example == "test")
        data = {} # <---
        example.add_value(data, "-test=bloo,blah")
        with pytest.raises(Exception):
            example.add_value(data, "-test=aweg")

    def test_add_value_custom_value(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : lambda x: int(x) + 2,
            "default" : 5,
          })
        assert(example == "test")
        data = {} # <---
        example.add_value(data, "-test=2")
        assert(example == "test")
        assert(data['test'] == 4)

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
        assert(name == "doot")

    def test_cmd(self):
        cmd_mock = mock.MagicMock()
        parser   = DootArgParser()
        result   = parser.parse([
            "doot", "list"
                               ],
            [], {"list": cmd_mock}, {}
            )

        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")

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
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert(result.on_fail(False).cmd.args.all() == True)

    def test_cmd_arg_fail(self):
        cmd_mock            = mock.MagicMock()
        type(cmd_mock).param_specs = mock.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])

        parser = DootArgParser()
        with pytest.raises(Exception):
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
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert(bool(result.on_fail(False).tasks.blah()))

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
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert(bool(result.on_fail(False).tasks["blah::bloo.blee"]()))

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
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "run")
        assert(bool(result.on_fail(False).tasks.list()))
        assert(result.on_fail(False).tasks.list.all() == True)

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
        assert(result.on_fail(False).head.name() == "doot")
        assert(bool(result.on_fail(False).tasks.list()))
        assert(result.on_fail(False).tasks.list.all() == False)

    def test_tasks_dup_fail(self):
        cmd_mock            = mock.MagicMock()
        type(cmd_mock).param_specs = mock.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])
        type(cmd_mock).name = mock.PropertyMock(return_value="list")

        parser = DootArgParser()
        with pytest.raises(Exception):
            parser.parse([
                "doot", "list", "-all", "list"
                         ],
                [], {}, {"list": cmd_mock}
            )
