#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import logging as logmod
import warnings
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
##-- end imports
logging = logmod.root

import pytest
import doot.errors
from doot.parsers.parser import DootArgParser
from doot.structs import DootParamSpec, DootTaskSpec

class TestParamSpec:

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
        with pytest.raises(doot.errors.DootParseError):
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

    def test_positional(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [1,2,3],
            "positional" : True
            })
        assert(example.positional is True)

    def test_invisible_str(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [1,2,3],
            "invisible" : True,
            })
        assert(str(example) == "")

    def test_not_invisible_str(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [1,2,3],
            "invisible" : False,
            })
        assert(str(example) != "")



class TestArgParser:

    def test_initial(self):
        parser = DootArgParser()
        parsed = parser.parse([
            "doot", "-v", "2", "blah"
                               ],
            doot_specs=[], cmds={}, tasks={})

        name = parsed.on_fail(False).head.name()
        assert(name == "doot")

    def test_cmd(self, mocker):
        cmd_mock = mocker.MagicMock()
        parser   = DootArgParser()
        result   = parser.parse([
            "doot", "list"
                               ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={}
            )

        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")

    def test_cmd_args(self, mocker):
        cmd_mock            = mocker.MagicMock()
        type(cmd_mock).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])

        parser = DootArgParser()
        result = parser.parse([
            "doot", "list", "-all"
                               ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={}
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert(result.on_fail(False).cmd.args.all() == True)

    def test_cmd_arg_fail(self, mocker):
        cmd_mock            = mocker.MagicMock()
        type(cmd_mock).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])

        parser = DootArgParser()
        with pytest.raises(Exception):
            parser.parse([
                "doot", "list", "-all", "-bloo"
            ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={}
        )

    def test_cmd_then_task(self, mocker):
        cmd_mock            = mocker.MagicMock()
        type(cmd_mock).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])
        task_mock            = mocker.MagicMock()
        type(task_mock).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])

        parser = DootArgParser()
        result = parser.parse([
            "doot", "list", "blah"
                               ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={"blah": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert("blah" in result.tasks)

    def test_cmd_then_complex_task(self, mocker):
        cmd_mock            = mocker.MagicMock()
        type(cmd_mock).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])
        task_mock            = mocker.MagicMock()
        type(task_mock).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])

        parser = DootArgParser()
        result = parser.parse([
            "doot", "list", "blah::bloo.blee"
                               ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={"blah::bloo.blee": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert( "blah::bloo.blee" in result.tasks)

    def test_task_args(self, mocker):
        """ check tasks can recieve args """
        task_mock            = mocker.MagicMock(DootTaskSpec)
        type(task_mock.ctor).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])
        type(task_mock).name = mocker.PropertyMock(return_value="basic::list")

        parser = DootArgParser()
        result = parser.parse([
            "doot", "basic::list", "-all"
                               ],
            doot_specs=[], cmds={}, tasks={"basic::list": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "run")
        assert(bool(result.on_fail(False).tasks["basic::list"]()))
        assert(result.on_fail(False).tasks["basic::list"].all() == True)

    def test_task_with_name_spaces(self, mocker):
        task_mock            = mocker.MagicMock()
        type(task_mock.ctor).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])
        type(task_mock).name = mocker.PropertyMock(return_value="simple task")

        parser = DootArgParser()
        result = parser.parse([
            "doot", "simple task", "-all"
                               ],
            doot_specs=[], cmds={}, tasks={"simple task": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "run")
        assert(bool(result.on_fail(False).tasks['simple task']()))
        assert(result.on_fail(False).tasks['simple task'].all() == True)

    def test_task_args_default(self, mocker):
        task_mock            = mocker.MagicMock()
        type(task_mock.ctor).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])
        type(task_mock).name = mocker.PropertyMock(return_value="list")

        parser = DootArgParser()
        result = parser.parse([
            "doot", "list", # no "-all"
                               ],
            doot_specs=[], cmds={}, tasks={"list": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(bool(result.on_fail(False).tasks.list()))
        assert(result.on_fail(False).tasks.list.all() == False)

    def test_tasks_dup_fail(self, mocker):
        cmd_mock            = mocker.MagicMock()
        type(cmd_mock).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="all")
            ])
        type(cmd_mock).name = mocker.PropertyMock(return_value="list")

        parser = DootArgParser()
        with pytest.raises(Exception):
            parser.parse([
                "doot", "list", "-all", "list"
                         ],
                doot_specs=[], cmds={}, tasks={"list": cmd_mock}
            )


    def test_positional_cmd_arg(self, mocker):
        cmd_mock            = mocker.MagicMock()
        type(cmd_mock).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="test", type=str, positional=True)
            ])
        type(cmd_mock).name = mocker.PropertyMock(return_value="example")

        parser = DootArgParser()
        result = parser.parse([
            "doot", "example", "blah"
                        ],
            doot_specs=[], cmds={"example": cmd_mock}, tasks={},
            )
        assert(result.cmd.name == "example")
        assert(result.cmd.args.test == "blah")

    def test_positional_cmd_arg_seq(self, mocker):
        cmd_mock            = mocker.MagicMock()
        type(cmd_mock).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="first", type=str, positional=True),
            DootParamSpec(name="second", type=str, positional=True)
            ])
        type(cmd_mock).name = mocker.PropertyMock(return_value="example")

        parser = DootArgParser()
        result = parser.parse([
            "doot", "example", "blah", "bloo"
                        ],
            doot_specs=[], cmds={"example": cmd_mock}, tasks={}
            )
        assert(result.cmd.args.first == "blah")
        assert(result.cmd.args.second == "bloo")


    def test_positional_task_arg(self, mocker):
        task_mock            = mocker.MagicMock(DootTaskSpec)
        type(task_mock.ctor).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="test", type=str, positional=True, default="")
                                                        ])
        type(task_mock).name = mocker.PropertyMock(return_value="example")

        parser = DootArgParser()
        result = parser.parse([
            "doot", "example", "blah"
                        ],
            doot_specs=[], cmds={}, tasks={"example": task_mock},
            )
        assert("example" in result.tasks)
        assert(result.tasks.example.test == "blah")

    def test_positional_taskarg_seq(self, mocker):
        task_mock            = mocker.MagicMock()
        type(task_mock.ctor).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="first", type=str, positional=True),
            DootParamSpec(name="second", type=str, positional=True)
            ])
        type(task_mock).name = mocker.PropertyMock(return_value="example")

        parser = DootArgParser()
        result = parser.parse([
            "doot", "example", "blah", "bloo"
                        ],
            doot_specs=[], cmds={}, tasks={"example": task_mock},
            )
        assert(result.tasks.example.first == "blah")
        assert(result.tasks.example.second == "bloo")
