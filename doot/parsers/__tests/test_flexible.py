#!/usr/bin/env python4
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
from doot._abstract import ArgParser_i, TaskBase_i
from doot.parsers.flexible import DootFlexibleParser
from doot.structs import DootParamSpec, DootTaskSpec, DootCodeReference
from doot.utils.mock_gen import mock_parse_cmd, mock_parse_task


@pytest.mark.parametrize("ctor", [DootFlexibleParser])
class TestArgParser:

    def test_initial(self, ctor):
        parser = ctor()
        assert(isinstance(parser, ArgParser_i))

    def test_cmd(self, ctor, mocker):
        cmd_mock                   = mock_parse_cmd(name="list")
        parser                     = ctor()

        result                     = parser.parse(["doot", "list"],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={}
            )

        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name()  == "list")

    def test_cmd_args(self, ctor, mocker):
        cmd_mock  = mock_parse_cmd( params=[DootParamSpec(name="all")])
        parser    = ctor()
        result    = parser.parse([
            "doot", "list", "-all"
                               ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={}
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert(result.on_fail(False).cmd.args.all() == True)

    def test_cmd_arg_fail(self, ctor, mocker):
        cmd_mock                   = mock_parse_cmd(params=[DootParamSpec(name="all")])

        parser = ctor()
        with pytest.raises(Exception):
            parser.parse([
                "doot", "list", "-all", "-bloo"
            ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={}
        )

    def test_cmd_then_task(self, ctor, mocker):
        cmd_mock                   = mock_parse_cmd(params=[DootParamSpec(name="all")])
        task_mock                  = mock_parse_task(params=[{"name":"all"}])

        parser = ctor()
        result = parser.parse([
            "doot", "list", "blah"
                               ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={"blah": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert("blah" in result.tasks)

    def test_cmd_then_complex_task(self, ctor, mocker):
        cmd_mock  = mock_parse_cmd(params=[DootParamSpec(name="all")])
        task_mock = mock_parse_task(params=[{"name":"all"}])

        parser    = ctor()
        result    = parser.parse([
            "doot", "list", "blah::bloo.blee"
                               ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={"blah::bloo.blee": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert( "blah::bloo.blee" in result.tasks)

    def test_task_args(self, ctor, mocker):
        """ check tasks can recieve args """
        cmd_mock                                    = mock_parse_cmd()
        task_mock                                   = mock_parse_task(params=[{"name":"all"}])

        parser                                      = ctor()
        result                                      = parser.parse([
            "doot", "basic::list", "-all"
                               ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"basic::list": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "run")
        assert(bool(result.on_fail(False).tasks["basic::list"]()))
        assert(result.on_fail(False).tasks["basic::list"].all() == True)

    def test_task_with_name_spaces(self, ctor, mocker):
        cmd_mock                   = mock_parse_cmd()
        task_mock                  = mock_parse_task(params=[{"name":"all"}])

        parser = ctor()
        result = parser.parse([
            "doot", "simple task", "-all"
                               ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"simple task": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "run")
        assert(bool(result.on_fail(False).tasks['simple task']()))
        assert(result.on_fail(False).tasks['simple task'].all() == True)

    def test_task_args_default(self, ctor, mocker):
        cmd_mock                   = mock_parse_cmd()
        task_mock                  = mock_parse_task(params=[{"name":"all"}])

        parser = ctor()
        result = parser.parse([
            "doot", "list", # no "-all"
                               ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"list": task_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(bool(result.on_fail(False).tasks.list()))
        assert(result.on_fail(False).tasks.list.all() == False)

    def test_tasks_dup_fail(self, ctor, mocker):
        cmd_mock                   = mock_parse_cmd()
        task_mock                  = mock_parse_task(params=[{"name":"all"}])

        parser = ctor()
        with pytest.raises(doot.errors.DootParseError):
            parser.parse([
                "doot", "list", "-all", "list"
                         ],
                doot_specs=[], cmds={"run": cmd_mock}, tasks={"list": task_mock}
            )

    def test_positional_cmd_arg(self, ctor, mocker):
        cmd_mock                   = mock_parse_cmd(params=[DootParamSpec("test", type=str, positional=True)])
        task_mock                  = mock_parse_task(params=[{"name":"key"}])

        parser = ctor()
        result = parser.parse([
            "doot", "example", "blah"
                        ],
            doot_specs=[], cmds={"example": cmd_mock}, tasks={"other": task_mock},
            )
        assert(result.cmd.name == "example")
        assert(result.cmd.args.test == "blah")

    def test_positional_cmd_arg_seq(self, ctor, mocker):
        cmd_mock                   = mock_parse_cmd(params=[
            DootParamSpec(name="first", type=str, positional=True),
            DootParamSpec(name="second", type=str, positional=True)
            ])
        task_mock                  = mock_parse_task(params=[{"name":"key"}])

        parser = ctor()
        result = parser.parse([
            "doot", "example", "blah", "bloo"
                        ],
            doot_specs=[], cmds={"example": cmd_mock}, tasks={}
            )
        assert(result.cmd.args.first == "blah")
        assert(result.cmd.args.second == "bloo")

    def test_positional_task_arg(self, ctor, mocker):
        cmd_mock                   = mock_parse_cmd()
        task_mock                  = mock_parse_task(params=[{"name":"test", "type":str, "positional":True, "default":""}])

        parser = ctor()
        result = parser.parse([
            "doot", "example", "blah"
                        ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"example": task_mock},
            )
        assert("example" in result.tasks)
        assert(result.tasks.example.test == "blah")

    def test_positional_taskarg_seq(self, ctor, mocker):
        cmd_mock                   = mock_parse_cmd()
        task_mock                  = mock_parse_task(params=[
            {"name":"first", "type":str, "positional":True},
            {"name":"second", "type":str, "positional":True}
            ])

        parser = ctor()
        result = parser.parse([
            "doot", "example", "blah", "bloo"
                        ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"example": task_mock},
            )
        assert(result.tasks.example.first == "blah")
        assert(result.tasks.example.second == "bloo")

    def test_simple_head_arg(self, ctor, mocker):
        param = DootParamSpec("key", bool)
        parser   = ctor()
        result   = parser.parse(["doot", "-key"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key is True)


    def test_simple_short_arg(self, ctor, mocker):
        param = DootParamSpec("key", bool)
        parser   = ctor()
        result   = parser.parse(["doot", "-k"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key is True)

    def test_simple_invert(self, ctor, mocker):
        param = DootParamSpec("key", bool)
        parser   = ctor()
        result   = parser.parse(["doot", "-no-key"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key is False)

    def test_simple_multi(self, ctor, mocker):
        param    = DootParamSpec("key", bool)
        param2   = DootParamSpec("other", bool)
        parser   = ctor()
        result   = parser.parse(["doot", "-no-key", "-other"],
            doot_specs=[param, param2], cmds={}, tasks={}
            )

        assert(result.head.args.key is False)
        assert(result.head.args.other is True)

    def test_simple_default(self, ctor, mocker):
        param    = DootParamSpec("key", bool)
        parser   = ctor()
        result   = parser.parse(["doot"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key is False)

    def test_simple_assign(self, ctor, mocker):
        param    = DootParamSpec("key", str, prefix="--")
        parser   = ctor()
        result   = parser.parse(["doot", "--key=blah"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key == "blah")


    def test_assign_fail_with_wrong_prefix(self, ctor, mocker):
        param    = DootParamSpec("key", str, prefix="-")
        parser   = ctor()

        with pytest.raises(doot.errors.DootParseError):
            parser.parse(["doot", "--key=blah"],
                doot_specs=[param], cmds={}, tasks={}
                )



    def test_simple_follow_assign(self, ctor, mocker):
        param    = DootParamSpec("key", str)
        parser   = ctor()
        result   = parser.parse(["doot", "-key", "blah"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key == "blah")


    def test_simple_prefix_change(self, ctor, mocker):
        param    = DootParamSpec("key", str, prefix="--")
        parser   = ctor()
        result   = parser.parse(["doot", "--key", "blah"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key == "blah")


    def test_simple_separator_change(self, ctor, mocker):
        param    = DootParamSpec("key", str, separator="%%", prefix="--")
        parser   = ctor()
        result   = parser.parse(["doot", "--key%%blah"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key == "blah")

    def test_simple_cmd(self, ctor, mocker):
        cmd_mock = mock_parse_cmd(params=[DootParamSpec(name="key")])
        parser   = ctor()
        result   = parser.parse(["doot", "list"],
            doot_specs=[], cmds={"list" : cmd_mock}, tasks={}
            )

        assert(result.cmd.name == "list")
        assert(result.cmd.args.key is False)

    def test_simple_cmd_arg(self, ctor, mocker):
        cmd_mock            = mocker.MagicMock()
        type(cmd_mock).param_specs = mocker.PropertyMock(return_value=[
            DootParamSpec(name="key")
            ])
        param = DootParamSpec("key", bool)
        parser   = ctor()
        result   = parser.parse(["doot", "list", '-key'],
            doot_specs=[], cmds={"list" : cmd_mock}, tasks={}
            )

        assert(result.cmd.name == "list")
        assert(result.cmd.args.key is True)

    def test_cmd_default(self, ctor, mocker):
        cmd_mock                   = mock_parse_cmd()
        task_mock                  = mock_parse_task(params=[{"name":"key"}])

        parser   = ctor()
        result   = parser.parse(["doot" , "val"],
            doot_specs=[], cmds={"run": cmd_mock }, tasks={"val": task_mock}
            )

        assert(result.cmd.name == "run")


    def test_simple_task(self, ctor, mocker):
        cmd_mock             = mock_parse_cmd()
        task_mock            = mock_parse_task(params=[{"name":"key"}])

        parser               = ctor()
        result               = parser.parse(["doot", "list", '-key'],
            doot_specs=[], cmds={"run": cmd_mock }, tasks={"list" : task_mock}
            )

        assert(result.cmd.name == "run")
        assert("list" in result.tasks)
        assert(result.tasks.list.key is True)


    def test_simple_task_sequence(self, ctor, mocker):
        cmd_mock   = mock_parse_cmd()
        task_mock  = mock_parse_task(params=[{"name":"key", "type":bool}])
        task_mock2 = mock_parse_task(params=[{"name":"other", "type":bool}])

        parser     = ctor()
        result     = parser.parse(["doot", "list", "-key", "blah", "-other"],
            doot_specs=[], cmds={"run": cmd_mock }, tasks={"list" : task_mock, "blah": task_mock2}
            )

        assert(result.cmd.name == "run")
        assert("list" in result.tasks)
        assert(result.tasks.list.key is True)
        assert("blah" in result.tasks)
        assert(result.tasks.blah.other is True)
