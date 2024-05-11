#!/usr/bin/env python4
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import warnings
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot

# ##-- end 1st party imports

doot._test_setup()

# ##-- 1st party imports
import doot.errors
from doot._abstract import ArgParser_i, Task_i, Command_i
from doot.parsers.flexible import DootFlexibleParser
from doot.structs import CodeReference, ParamSpec, TaskSpec

# ##-- end 1st party imports

logging = logmod.root

@pytest.mark.parametrize("ctor", [DootFlexibleParser])
class TestArgParser:

    @pytest.fixture(scope="function")
    def cmd_mock(self, mocker):
        return mocker.MagicMock(spec=Command_i, param_specs=[ParamSpec(name="all")])

    @pytest.fixture(scope="function")
    def spec_mock(self, mocker):
        return self.make_spec_mock(mocker)

    def make_spec_mock(self, mocker):
        task_mock                 = mocker.MagicMock(spec=TaskSpec, ctor=mocker.MagicMock(spec=CodeReference))
        ctor_mock                 = mocker.Mock()
        ctor_mock.param_specs     = []
        task_mock.ctor.try_import = mocker.Mock(return_value=ctor_mock)
        task_mock.extra           = TomlGuard({"cli": [ParamSpec(name="all")]})

        return task_mock

    def test_initial(self, ctor):
        parser = ctor()
        assert(isinstance(parser, ArgParser_i))

    def test_cmd(self, ctor, mocker, cmd_mock):
        parser                     = ctor()

        result                     = parser.parse(["doot", "list"],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={}
            )

        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name()  == "list")

    def test_cmd_args(self, ctor, mocker, cmd_mock):
        parser    = ctor()
        result    = parser.parse([
            "doot", "list", "-all"
                                 ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={}
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert(result.on_fail(False).cmd.args.all() == True)

    def test_cmd_arg_fail(self, ctor, mocker, cmd_mock):
        parser = ctor()
        with pytest.raises(Exception):
            parser.parse([
                "doot", "list", "-all", "-bloo"
            ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={}
        )

    def test_cmd_then_task(self, ctor, mocker, cmd_mock, spec_mock):
        cmd_mock    = mocker.MagicMock(spec=Command_i, param_specs=[ParamSpec(name="all")])
        parser      = ctor()
        result      = parser.parse([
            "doot", "list", "agroup::blah"
                               ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={"agroup::blah": spec_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert("agroup::blah" in result.tasks)

    def test_cmd_then_complex_task(self, ctor, mocker, cmd_mock, spec_mock):
        parser    = ctor()
        result    = parser.parse([
            "doot", "list", "blah::bloo.blee"
                               ],
            doot_specs=[], cmds={"list": cmd_mock}, tasks={"blah::bloo.blee": spec_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "list")
        assert( "blah::bloo.blee" in result.tasks)

    def test_task_args(self, ctor, mocker, cmd_mock, spec_mock):
        """ check tasks can recieve args """
        parser                                      = ctor()
        result                                      = parser.parse([
            "doot", "basic::list", "-all"
                               ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"basic::list": spec_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "run")
        assert(bool(result.on_fail(False).tasks["basic::list"]()))
        assert(result.on_fail(False).tasks["basic::list"].all() == True)

    def test_task_with_name_spaces(self, ctor, mocker, cmd_mock, spec_mock):
        parser = ctor()
        result = parser.parse([
            "doot", "agroup::simple task", "-all"
                               ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"agroup::simple task": spec_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(result.on_fail(False).cmd.name() == "run")
        assert(bool(result.on_fail(False).tasks['agroup::simple task']()))
        assert(result.on_fail(False).tasks['agroup::simple task'].all() == True)

    def test_task_args_default(self, ctor, mocker, cmd_mock, spec_mock):
        parser = ctor()
        result = parser.parse([
            "doot", "agroup::list", # no "-all"
                               ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"agroup::list": spec_mock},
            )
        assert(result.on_fail(False).head.name() == "doot")
        assert(bool(result.on_fail(False).tasks['agroup::list']()))
        assert(result.on_fail(False).tasks['agroup::list'].all() == False)

    def test_tasks_dup_fail(self, ctor, mocker, cmd_mock, spec_mock):
        cmd_mock, task_mock    = cmd_mock, spec_mock
        parser = ctor()
        with pytest.raises(doot.errors.DootParseError):
            parser.parse([
                "doot", "agroup::list", "-all", "agroup::list"
                         ],
                doot_specs=[], cmds={"run": cmd_mock}, tasks={"agroup::list": task_mock}
            )

    def test_positional_cmd_arg(self, ctor, mocker, cmd_mock, spec_mock):
        cmd_mock.param_specs.append(ParamSpec(name="test", type=str, positional=True))
        spec_mock.extra.cli.append(ParamSpec(name="key"))
        parser = ctor()
        result = parser.parse([
            "doot", "example", "blah"
                        ],
            doot_specs=[], cmds={"example": cmd_mock}, tasks={"other": spec_mock},
            )
        assert(result.cmd.name == "example")
        assert(result.cmd.args.test == "blah")

    def test_positional_cmd_arg_seq(self, ctor, mocker, cmd_mock, spec_mock):
        cmd_mock.param_specs.append(ParamSpec(name="first", type=str, positional=True))
        cmd_mock.param_specs.append(ParamSpec(name="second", type=str, positional=True))

        parser = ctor()
        result = parser.parse([
            "doot", "example", "blah", "bloo"
                        ],
            doot_specs=[], cmds={"example": cmd_mock}, tasks={}
            )
        assert(result.cmd.args.first == "blah")
        assert(result.cmd.args.second == "bloo")

    def test_positional_task_arg(self, ctor, mocker, cmd_mock, spec_mock):
        spec_mock.extra.cli.append(ParamSpec.build({"name":"test", "type":str, "positional":True, "default":""}))

        parser = ctor()
        result = parser.parse([
            "doot", "agroup::example", "blah"
                        ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"agroup::example": spec_mock},
            )
        assert("agroup::example" in result.tasks)
        assert(result.tasks['agroup::example'].test == "blah")

    def test_positional_taskarg_seq(self, ctor, mocker, cmd_mock, spec_mock):
        spec_mock.extra.cli.append(ParamSpec.build({"name":"first", "type":str, "positional":True}))
        spec_mock.extra.cli.append(ParamSpec.build({"name":"second", "type":str, "positional":True}))

        parser = ctor()
        result = parser.parse([
            "doot", "agroup::example", "blah", "bloo"
                        ],
            doot_specs=[], cmds={"run": cmd_mock}, tasks={"agroup::example": spec_mock},
            )
        assert(result.tasks['agroup::example'].first == "blah")
        assert(result.tasks['agroup::example'].second == "bloo")

    def test_simple_head_arg(self, ctor, mocker):
        param = ParamSpec(name="key", type=bool)
        parser   = ctor()
        result   = parser.parse(["doot", "-key"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key is True)


    def test_simple_short_arg(self, ctor, mocker):
        param = ParamSpec(name="key", type=bool)
        parser   = ctor()
        result   = parser.parse(["doot", "-k"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key is True)

    def test_simple_invert(self, ctor, mocker):
        param = ParamSpec(name="key", type=bool)
        parser   = ctor()
        result   = parser.parse(["doot", "-no-key"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key is False)

    def test_simple_multi(self, ctor, mocker):
        param    = ParamSpec(name="key", type=bool)
        param2   = ParamSpec(name="other", type=bool)
        parser   = ctor()
        result   = parser.parse(["doot", "-no-key", "-other"],
            doot_specs=[param, param2], cmds={}, tasks={}
            )

        assert(result.head.args.key is False)
        assert(result.head.args.other is True)

    def test_simple_default(self, ctor, mocker):
        param    = ParamSpec(name="key", type=bool)
        parser   = ctor()
        result   = parser.parse(["doot"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key is False)

    def test_simple_assign(self, ctor, mocker):
        param    = ParamSpec(name="key", type=str, prefix="--")
        parser   = ctor()
        result   = parser.parse(["doot", "--key=blah"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key == "blah")


    def test_assign_fail_with_wrong_prefix(self, ctor, mocker):
        param    = ParamSpec(name="key", type=str, prefix="-")
        parser   = ctor()

        with pytest.raises(doot.errors.DootParseError):
            parser.parse(["doot", "--key=blah"],
                doot_specs=[param], cmds={}, tasks={}
                )



    def test_simple_follow_assign(self, ctor, mocker):
        param    = ParamSpec(name="key", type=str)
        parser   = ctor()
        result   = parser.parse(["doot", "-key", "blah"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key == "blah")


    def test_simple_prefix_change(self, ctor, mocker):
        param    = ParamSpec(name="key", type=str, prefix="--")
        parser   = ctor()
        result   = parser.parse(["doot", "--key", "blah"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key == "blah")


    def test_simple_separator_change(self, ctor, mocker):
        param    = ParamSpec(name="key", type=str, separator="%%", prefix="--")
        parser   = ctor()
        result   = parser.parse(["doot", "--key%%blah"],
            doot_specs=[param], cmds={}, tasks={}
            )

        assert(result.head.args.key == "blah")

    def test_simple_cmd(self, ctor, mocker, cmd_mock):
        cmd_mock.param_specs.append(ParamSpec(name="key"))
        parser   = ctor()
        result   = parser.parse(["doot", "list"],
            doot_specs=[], cmds={"list" : cmd_mock}, tasks={}
            )

        assert(result.cmd.name == "list")
        assert(result.cmd.args.key is False)

    def test_simple_cmd_arg(self, ctor, mocker, cmd_mock):
        cmd_mock.param_specs.append(ParamSpec(name="key"))
        parser   = ctor()
        result   = parser.parse(["doot", "list", '-key'],
            doot_specs=[], cmds={"list" : cmd_mock}, tasks={}
            )

        assert(result.cmd.name == "list")
        assert(result.cmd.args.key is True)

    def test_cmd_default(self, ctor, mocker, cmd_mock, spec_mock):
        spec_mock.extra.cli.append(ParamSpec.build({"name":"key"}))

        parser   = ctor()
        result   = parser.parse(["doot" , "agroup::val"],
            doot_specs=[], cmds={"run": cmd_mock }, tasks={"agroup::val": spec_mock}
            )

        assert(result.cmd.name == "run")


    def test_simple_task(self, ctor, mocker, cmd_mock, spec_mock):
        spec_mock.extra.cli.append(ParamSpec.build({"name":"key"}))

        parser               = ctor()
        result               = parser.parse(["doot", "agroup::list", '-key'],
            doot_specs=[], cmds={"run": cmd_mock }, tasks={"agroup::list" : spec_mock}
            )

        assert(result.cmd.name == "run")
        assert("agroup::list" in result.tasks)
        assert(result.tasks['agroup::list'].key is True)


    def test_simple_task_sequence(self, ctor, mocker, cmd_mock):
        spec_1 = self.make_spec_mock(mocker)
        spec_2 = self.make_spec_mock(mocker)

        spec_1.extra.cli.append(ParamSpec.build({"name":"key", "type":bool}))
        spec_2.extra.cli.append(ParamSpec.build({"name":"other", "type":bool}))

        parser     = ctor()
        result     = parser.parse(["doot", "agroup::list", "-key", "agroup::blah", "-other"],
            doot_specs=[], cmds={"run": cmd_mock }, tasks={"agroup::list" : spec_1, "agroup::blah": spec_2}
            )

        assert(result.cmd.name == "run")
        assert("agroup::list" in result.tasks)
        assert(result.tasks['agroup::list'].key is True)
        assert("agroup::blah" in result.tasks)
        assert(result.tasks['agroup::blah'].other is True)
