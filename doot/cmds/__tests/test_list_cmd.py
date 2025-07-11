#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN201, ANN001, B011, E402
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import contextlib
import datetime
import enum
import functools as ftz
import io
import itertools as itz
import logging as logmod
import pathlib as pl
import sys
import unittest
import warnings
from unittest import mock
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
from jgdv import Mixin, Proto
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.workflow.structs import TaskSpec
from doot.util.factory import TaskFactory

# ##-- end 1st party imports

# ##-| Local
from .. import list_cmd as list_mod
from .._interface import Command_p
from ..list_cmd import ListCmd

# # End of Imports.

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

# isort: on
# ##-- end types

logging = logmod.root

##-- toml strings

empty_args = """
# No args are specified
[cmds]
"""

missing_main_arg = """
# This has None of the main listing types
[[cmds.blah]]
[cmds.blah.args]
by_source = false
pattern   = ""
"""

minimal_example = """
[[cmds.list]]
[cmds.list.args]
tasks = true
pattern = ""
"""

simple_pattern = """
[[cmds.list]]
[cmds.list.args]
tasks    = true
pattern  = ".+simple"
"""

partial_pattern = """
[[cmds.list]]
[cmds.list.args]
tasks = true
pattern = ".+simp"
"""

group_pattern = """
[[cmds.list]]
[cmds.list.args]
tasks = true
pattern = ".+simp::"
"""

list_group = """
[[cmds.list]]
[cmds.list.args]
tasks = true
group-by = "group"
"""

list_by_source = """
[[cmds.list]]
[cmds.list.args]
tasks = true
group-by = "source"
"""

list_locs = """
[[cmds.list]]
[cmds.list.args]
locs = true
"""

list_loggers = """
[[cmds.list]]
[cmds.list.args]
loggers = true
"""

list_flags = """
[[cmds.list]]
[cmds.list.args]
flags = true
"""

list_actions = """
[[cmds.list]]
[cmds.list.args]
actions = true
"""

list_plugins = """
[[cmds.list]]
[cmds.list.args]
plugins = true
"""

##-- end toml strings
factory : TaskFactory = TaskFactory()
##--|
class TestListCmd:

    def test_initial(self):
        obj = ListCmd()
        assert(isinstance(obj, Command_p))

    def test_param_specs(self):
        obj    = ListCmd()
        result = obj.param_specs()
        expect = ["tasks", "group-by", "dependencies", "internal",
                  "locs", "loggers", "flags", "actions", "plugins" ]
        assert(isinstance(result, list))
        names = [x.name for x in result]
        for x in expect:
            assert(x in names), names

    def test_call_bad_cli_args(self, mocker):
        guard = ChainGuard.read(missing_main_arg)
        mocker.patch("doot.args", new=guard)
        obj = ListCmd()

        with pytest.raises(doot.errors.DootError):
            obj(idx=0, tasks={}, plugins={})

    def test_call_all_empty(self, caplog, mocker):
        caplog.set_level(logmod.NOTSET, logger=doot.report.log.name)
        guard = ChainGuard.read(minimal_example)
        mocker.patch("doot.args", new=guard)
        mocker.patch("doot.loaded_tasks", new=guard)
        obj    = ListCmd()
        obj(idx=0, tasks={}, plugins={"reporter": [mocker.stub("Reporter Stub")]})
        message_set = {x for x in caplog.messages}
        assert("!! No Tasks Defined" in message_set)

    def test_call_all_not_empty(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        mocker.patch("doot.args", new=ChainGuard.read(minimal_example))
        obj = ListCmd()
        mock_class1 = mocker.MagicMock(type)
        mock_class1.__module__ = "builtins"
        mock_class1.__name__   = "type"
        mock_class2 = mocker.MagicMock(type)
        mock_class2.__module__ = "builtins"
        mock_class2.__name__   = "other.type"
        plugin_mock = {"reporter": [mocker.stub("Reporter Stub")]}
        job_mock = {
            "simple" : factory.build({"group": "blah", "name": "simple"}), # "ctor": mock_class1}),
            "other"  : factory.build({"group": "bloo", "name": "other"}),  # "ctor": mock_class2})
        }
        obj(idx=0, tasks=job_mock, plugins=plugin_mock)
        message_set : set[str] = {x.message.lower().strip() for x in caplog.records}

        assert("registered tasks/jobs:" in message_set)
        assert(any(x.startswith("*    blah::") for x in message_set) )
        assert(any(x.startswith("*    bloo::") for x in message_set) )
        assert(any(x.startswith("simple") for x in message_set) )
        assert(any(x.startswith("other") for x in message_set) )

    def test_list_even_with_ctor_failure(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        mocker.patch("doot.args", new=ChainGuard.read(minimal_example))
        obj = ListCmd()
        mock_class1 = "doot.workflow:DootTask"
        mock_class2 = "doot.workflow:DootJob_bad"
        plugin_mock = {"reporter": [mocker.stub("Reporter Stub")]}
        job_mock = {
            "simple" : factory.build({"group": "blah", "name": "simple", "ctor": mock_class1}),
            "other"  : factory.build({"group": "bloo", "name": "other", "ctor": mock_class2}),
        }
        obj(idx=0, tasks=job_mock, plugins=plugin_mock)
        message_set : set[str] = {x.message.lower().strip() for x in caplog.records}

        assert("registered tasks/jobs:" in message_set)
        assert(any(x.startswith("simple") for x in message_set) )
        assert(any(x.startswith("ctor import failed") for x in message_set) )

    def test_call_target_not_empty(self, caplog, mocker):
        message_set  : set[str]
        obj          : Command_p
        plugin_mock  : dict
        job_mock     : dict
        result       : Any
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        mocker.patch("doot.args", new=ChainGuard.read(simple_pattern))
        obj          = ListCmd()
        plugin_mock  = {"reporter": [mocker.stub("Reporter Stub")]}
        job_mock     = {
            "simple" : factory.build({"group": "blah", "name": "simple"}),
            "other"  : factory.build({"group": "bloo", "name": "other"}),
        }
        result       = obj(idx=0, tasks=job_mock, plugins=plugin_mock)
        message_set  = {x.message.lower().strip() for x in caplog.records}

        assert("registered tasks/jobs:" in message_set)
        assert( any(x.startswith("simple") for x in message_set) )
        assert( not any(x.startswith("other") for x in message_set) )

    def test_call_partial_target_not_empty(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        mocker.patch("doot.args", new=ChainGuard.read(partial_pattern))
        obj = ListCmd()
        plugin_mock = {"reporter": [mocker.stub("Reporter Stub")]}
        job_mock = { "blah::simple"    : factory.build({"group": "blah", "name": "simple"}),
                     "bloo::other"     : factory.build({"group": "bloo", "name": "other"}),
                     "bloo::diffSimple": factory.build({"group": "bloo", "name": "diffSimple"}),
                    }
        result = obj(idx=0, tasks=job_mock, plugins=plugin_mock)
        message_set : set[str] = {x.message.lower().strip() for x in caplog.records}

        assert("registered tasks/jobs:" in message_set)
        assert( any(x.startswith("simple") for x in message_set) )
        assert( any(x.startswith("diffsimple") for x in message_set) )

class TestListings:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_list_tasks_matches(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        mocker.patch("doot.args", new=ChainGuard.read(simple_pattern))
        obj = ListCmd()
        tasks = []
        match obj._list_tasks(0, tasks):
            case []:
                assert(False)
            case [*xs]:
                assert(True)
            case _:
                assert(False)

    def test_list_group_matches(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        mocker.patch("doot.args", new=ChainGuard.read(group_pattern))
        obj = ListCmd()
        tasks = []
        match obj._list_tasks(0, tasks):
            case []:
                assert(False)
            case [*xs]:
                assert(True)
            case _:
                assert(False)

    def test_list_all_by_group(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        mocker.patch("doot.args", new=ChainGuard.read(list_group))
        obj = ListCmd()
        tasks = []
        match obj._list_tasks(0, tasks):
            case []:
                assert(False)
            case [*xs]:
                assert(True)
            case _:
                assert(False)

    def test_list_by_source(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        mocker.patch("doot.args", new=ChainGuard.read(list_by_source))
        obj = ListCmd()
        tasks = []
        match obj._list_tasks(0, tasks):
            case [*xs]:
                assert(True)
            case _:
                assert(False)

    def test_list_locations(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        mocker.patch("doot.args", new=ChainGuard.read(list_locs))
        obj = ListCmd()
        match obj._list_locations():
            case []:
                assert(False)
            case [*xs]:
                assert(True)
            case _:
                assert(False)

    def test_list_loggers(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        mocker.patch("doot.args", new=ChainGuard.read(list_loggers))
        obj = ListCmd()
        match obj._list_loggers():
            case []:
                assert(False)
            case [*xs]:
                assert(True)
            case _:
                assert(False)

    def test_list_flags(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        mocker.patch("doot.args", new=ChainGuard.read(list_flags))
        obj = ListCmd()
        match obj._list_flags():
            case []:
                assert(False)
            case [*xs]:
                assert(True)
            case _:
                assert(False)

    def test_list_actions(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        mocker.patch("doot.args", new=ChainGuard.read(list_actions))
        obj = ListCmd()
        plugins = ChainGuard({"action":[]})
        match obj._list_actions(plugins):
            case []:
                assert(False)
            case [*xs]:
                assert(True)
            case _:
                assert(False)

    def test_list_plugins(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        mocker.patch("doot.args", new=ChainGuard.read(list_plugins))
        obj = ListCmd()
        plugins = ChainGuard({})
        match obj._list_plugins(plugins):
            case []:
                assert(False)
            case [*xs]:
                assert(True)
            case _:
                assert(False)
