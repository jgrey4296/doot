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
from doot._abstract import ArgParser_i
from doot.parsers.flexible import DootFlexibleParser
from doot.structs import DootParamSpec, DootTaskSpec
from doot.utils.mock_gen import mock_parse_cmd, mock_parse_task


class TestArgParser:

    def test_initial(self):
        parser = DootFlexibleParser()
        assert(isinstance(parser, ArgParser_i))

    def test_cmd(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker)
        parser                     = DootFlexibleParser()
        result                     = parser.parse([
            "doot", "list"
                               ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={}
            )

        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")

    def test_cmd_args(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker, [DootParamSpec(name="all")])
        parser = DootFlexibleParser()
        result = parser.parse([
            "doot", "list", "-all"
                               ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={}
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert(result.on_fail(False).cmd.args.all() == True)

    def test_cmd_arg_fail(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker, [DootParamSpec(name="all")])

        parser = DootFlexibleParser()
        with pytest.raises(Exception):
            parser.parse([
                "doot", "list", "-all", "-bloo"
            ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={}
        )

    def test_cmd_then_task(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker, [DootParamSpec(name="all")])
        task_mock                  = mock_parse_task(mocker, [DootParamSpec(name="all")])

        parser = DootFlexibleParser()
        result = parser.parse([
            "doot", "list", "blah"
                               ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={"blah": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert("blah" in result.tasks)

    def test_cmd_then_complex_task(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker, [DootParamSpec(name="all")])
        task_mock                  = mock_parse_task(mocker, [DootParamSpec(name="all")])

        parser = DootFlexibleParser()
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
        cmd_mock                   = mock_parse_cmd(mocker)
        task_mock                  = mock_parse_task(mocker, [DootParamSpec(name="all")])

        parser = DootFlexibleParser()
        result = parser.parse([
            "doot", "basic::list", "-all"
                               ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"basic::list": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "run")
        assert(bool(result.on_fail(False).tasks["basic::list"]()))
        assert(result.on_fail(False).tasks["basic::list"].all() == True)

    def test_task_with_name_spaces(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker)
        task_mock                  = mock_parse_task(mocker, [DootParamSpec(name="all")])

        parser = DootFlexibleParser()
        result = parser.parse([
            "doot", "simple task", "-all"
                               ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"simple task": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "run")
        assert(bool(result.on_fail(False).tasks['simple task']()))
        assert(result.on_fail(False).tasks['simple task'].all() == True)

    def test_task_args_default(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker)
        task_mock                  = mock_parse_task(mocker, [DootParamSpec(name="all")])

        parser = DootFlexibleParser()
        result = parser.parse([
            "doot", "list", # no "-all"
                               ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"list": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(bool(result.on_fail(False).tasks.list()))
        assert(result.on_fail(False).tasks.list.all() == False)

    def test_tasks_dup_fail(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker)
        task_mock                  = mock_parse_task(mocker, [DootParamSpec(name="all")])

        parser = DootFlexibleParser()
        with pytest.raises(Exception):
            parser.parse([
                "doot", "list", "-all", "list"
                         ],
                doot_specs=[], cmds={"run": cmd_mock}, tasks={"list": task_mock}
            )

    def test_positional_cmd_arg(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker, [DootParamSpec("test", type=str, positional=True)])
        task_mock                  = mock_parse_task(mocker, [DootParamSpec(name="key")])

        parser = DootFlexibleParser()
        result = parser.parse([
            "doot", "example", "blah"
                        ],
            doot_specs=[], cmds={"example": cmd_mock}, tasks={"other": task_mock},
            )
        assert(result.cmd.name == "example")
        assert(result.cmd.args.test == "blah")

    def test_positional_cmd_arg_seq(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker, [
                                                             DootParamSpec(name="first", type=str, positional=True),
                                                             DootParamSpec(name="second", type=str, positional=True)
                                                    ])
        task_mock                  = mock_parse_task(mocker, [DootParamSpec(name="key")])

        parser = DootFlexibleParser()
        result = parser.parse([
            "doot", "example", "blah", "bloo"
                        ],
            doot_specs=[], cmds={"example": cmd_mock}, tasks={}
            )
        assert(result.cmd.args.first == "blah")
        assert(result.cmd.args.second == "bloo")

    def test_positional_task_arg(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker)
        task_mock                  = mock_parse_task(mocker, [DootParamSpec(name="test", type=str, positional=True, default="")])

        parser = DootFlexibleParser()
        result = parser.parse([
            "doot", "example", "blah"
                        ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"example": task_mock},
            )
        assert("example" in result.tasks)
        assert(result.tasks.example.test == "blah")

    def test_positional_taskarg_seq(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker)
        task_mock                  = mock_parse_task(mocker, [
            DootParamSpec(name="first", type=str, positional=True),
            DootParamSpec(name="second", type=str, positional=True)
            ])

        parser = DootFlexibleParser()
        result = parser.parse([
            "doot", "example", "blah", "bloo"
                        ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"example": task_mock},
            )
        assert(result.tasks.example.first == "blah")
        assert(result.tasks.example.second == "bloo")

    def test_simple_head_arg(self, mocker):
        param = DootParamSpec("key", bool)
        parser   = DootFlexibleParser()
        result   = parser.parse(["doot", "-key"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key is True)


    def test_simple_short_arg(self, mocker):
        param = DootParamSpec("key", bool)
        parser   = DootFlexibleParser()
        result   = parser.parse(["doot", "-k"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key is True)

    def test_simple_invert(self, mocker):
        param = DootParamSpec("key", bool)
        parser   = DootFlexibleParser()
        result   = parser.parse(["doot", "-no-key"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key is False)

    def test_simple_multi(self, mocker):
        param    = DootParamSpec("key", bool)
        param2   = DootParamSpec("other", bool)
        parser   = DootFlexibleParser()
        result   = parser.parse(["doot", "-no-key", "-other"],
            doot_specs=[param, param2], cmds={}, tasks={}
            )

        assert(result.head.args.key is False)
        assert(result.head.args.other is True)

    def test_simple_default(self, mocker):
        param    = DootParamSpec("key", bool)
        parser   = DootFlexibleParser()
        result   = parser.parse(["doot"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key is False)

    def test_simple_assign(self, mocker):
        param    = DootParamSpec("key", str)
        parser   = DootFlexibleParser()
        result   = parser.parse(["doot", "-key=blah"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key == "blah")


    def test_simple_follow_assign(self, mocker):
        param    = DootParamSpec("key", str)
        parser   = DootFlexibleParser()
        result   = parser.parse(["doot", "-key", "blah"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key == "blah")


    def test_simple_prefix_change(self, mocker):
        param    = DootParamSpec("key", str, prefix="--")
        parser   = DootFlexibleParser()
        result   = parser.parse(["doot", "--key", "blah"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key == "blah")


    def test_simple_separator_change(self, mocker):
        param    = DootParamSpec("key", str, separator="%%")
        parser   = DootFlexibleParser()
        result   = parser.parse(["doot", "-key%%blah"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key == "blah")

    def test_simple_cmd(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker, [DootParamSpec(name="key")])

        parser   = DootFlexibleParser()
        result   = parser.parse(["doot", "list"],
            doot_specs=[], cmds={"list" : cmd_mock}, tasks={}
            )

        assert(result.cmd.name == "list")
        assert(result.cmd.args.key is False)

    def test_simple_cmd_arg(self, mocker):
        cmd_mock            = mocker.MagicMock()
        type(cmd_mock).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="key")
            ])
        param = DootParamSpec("key", bool)
        parser   = DootFlexibleParser()
        result   = parser.parse(["doot", "list", '-key'],
            doot_specs=[], cmds={"list" : cmd_mock}, tasks={}
            )

        assert(result.cmd.name == "list")
        assert(result.cmd.args.key is True)

    def test_cmd_default(self, mocker):
        cmd_mock                   = mock_parse_cmd(mocker)
        task_mock                  = mock_parse_task(mocker, [DootParamSpec(name="key")])

        parser   = DootFlexibleParser()
        result   = parser.parse(["doot" , "val"],
            doot_specs=[], cmds={"run": cmd_mock }, tasks={"val": task_mock}
            )

        assert(result.cmd.name == "run")


    def test_simple_task(self, mocker):
        cmd_mock            = mock_parse_cmd(mocker)
        task_mock            = mock_parse_task(mocker, [DootParamSpec(name="key")])

        parser   = DootFlexibleParser()
        result   = parser.parse(["doot", "list", '-key'],
            doot_specs=[], cmds={"run": cmd_mock }, tasks={"list" : task_mock}
            )

        assert(result.cmd.name == "run")
        assert("list" in result.tasks)
        assert(result.tasks.list.key is True)


    def test_simple_task_sequence(self, mocker):
        cmd_mock = mock_parse_cmd(mocker)
        task_mock                    = mock_parse_task(mocker, [DootParamSpec("key", type=bool)])
        task_mock2                   = mock_parse_task(mocker, [DootParamSpec("other", type=bool)])

        parser   = DootFlexibleParser()
        result   = parser.parse(["doot", "list", "-key", "blah", "-other"],
            doot_specs=[], cmds={"run": cmd_mock }, tasks={"list" : task_mock, "blah": task_mock2}
            )

        assert(result.cmd.name == "run")
        assert("list" in result.tasks)
        assert(result.tasks.list.key is True)
        assert("blah" in result.tasks)
        assert(result.tasks.blah.other is True)
