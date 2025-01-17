#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN201, ANN001
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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from unittest import mock
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
from jgdv.structs.chainguard import ChainGuard
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot

# ##-- end 1st party imports

doot._test_setup()

# ##-- 1st party imports
import doot.errors
from doot._abstract import Command_i
from doot.cmds.list_cmd import ListCmd
from doot.structs import TaskSpec

# ##-- end 1st party imports

logging = logmod.root


class TestListCmd:
    def test_initial(self):
        obj = ListCmd()
        assert(isinstance(obj, Command_i))

    def test_param_specs(self):
        obj    = ListCmd()
        result = obj.param_specs
        assert(isinstance(result, list))
        names = [x.name for x in result]
        assert("dependencies"in names)
        assert("pattern" in names)
        assert("help" in names)

    def test_call_bad_cli_args(self, mocker):
        guard = ChainGuard.read(
"""
[cmd.args]
by_source = false
pattern   = ""
""")
        mocker.patch("doot.args", new=guard)
        obj = ListCmd()

        with pytest.raises(doot.errors.DootError):
            obj({}, {})

    def test_call_all_empty(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        guard = ChainGuard.read(
"""
[cmd.args]
tasks = true
pattern = ""
""")
        mocker.patch("doot.args", new=guard)
        obj    = ListCmd()
        obj({}, {"reporter": [mocker.stub("Reporter Stub")]})
        message_set = {x.message for x in caplog.records}
        assert("!! No Tasks Defined" in message_set)


    def test_call_all_not_empty(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
tasks = true
pattern = ""
"""))
        obj = ListCmd()
        mock_class1 = mocker.MagicMock(type)
        mock_class1.__module__ = "builtins"
        mock_class1.__name__   = "type"
        mock_class2 = mocker.MagicMock(type)
        mock_class2.__module__ = "builtins"
        mock_class2.__name__   = "other.type"
        plugin_mock = {"reporter": [mocker.stub("Reporter Stub")]}
        job_mock = {
            "simple" : TaskSpec.build({"group": "blah", "name": "simple"}), # "ctor": mock_class1}),
            "other"  : TaskSpec.build({"group": "bloo", "name": "other"}),  # "ctor": mock_class2})
            }
        obj(job_mock, plugin_mock)
        message_set : set[str] = {x.message.lower().strip() for x in caplog.records}

        assert("registered tasks/jobs:" in message_set)
        assert(any(x.startswith("*    blah::") for x in message_set) )
        assert(any(x.startswith("*    bloo::") for x in message_set) )
        assert(any(x.startswith("simple") for x in message_set) )
        assert(any(x.startswith("other") for x in message_set) )

    def test_list_even_with_ctor_failure(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
tasks = true
pattern = ""
"""))
        obj = ListCmd()
        mock_class1 = "doot.task:DootTask"
        mock_class2 = "doot.task:DootJob_bad"
        plugin_mock = {"reporter": [mocker.stub("Reporter Stub")]}
        job_mock = {
            "simple" : TaskSpec.build({"group": "blah", "name": "simple", "ctor": mock_class1}),
            "other"  : TaskSpec.build({"group": "bloo", "name": "other", "ctor": mock_class2}),
            }
        obj(job_mock, plugin_mock)
        message_set : set[str] = {x.message.lower().strip() for x in caplog.records}

        assert("registered tasks/jobs:" in message_set)
        assert(any(x.startswith("simple") for x in message_set) )
        assert(any(x.startswith("ctor import failed") for x in message_set) )


    def test_call_target_not_empty(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
tasks = true
pattern = ".+simple"
"""))
        obj = ListCmd()
        plugin_mock  = {"reporter": [mocker.stub("Reporter Stub")]}
        job_mock = {
                       "simple" : TaskSpec.build({"group": "blah", "name": "simple"}),
                       "other"  : TaskSpec.build({"group": "bloo", "name": "other"}),
            }
        result = obj(job_mock, plugin_mock)
        message_set : set[str] = {x.message.lower().strip() for x in caplog.records}

        assert("registered tasks/jobs:" in message_set)
        assert( any(x.startswith("simple") for x in message_set) )
        assert( not any(x.startswith("other") for x in message_set) )

    def test_call_partial_target_not_empty(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
tasks = true
pattern = ".+simp"
"""))
        obj = ListCmd()
        plugin_mock = {"reporter": [mocker.stub("Reporter Stub")]}
        job_mock = { "blah::simple"    : TaskSpec.build({"group": "blah", "name": "simple"}),
                     "bloo::other"     : TaskSpec.build({"group": "bloo", "name": "other"}),
                     "bloo::diffSimple": TaskSpec.build({"group": "bloo", "name": "diffSimple"}),
                    }
        result = obj(job_mock, plugin_mock)
        message_set : set[str] = {x.message.lower().strip() for x in caplog.records}

        assert("registered tasks/jobs:" in message_set)
        assert( any(x.startswith("simple") for x in message_set) )
        assert( any(x.startswith("diffsimple") for x in message_set) )


@pytest.mark.skip
class TestListings:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133


    def test_list_tasks_matches(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
"""))
        obj = ListCmd()


    def test_list_group_matches(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
"""))
        obj = ListCmd()


    def test_list_all_by_group(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
"""))
        obj = ListCmd()


    def test_list_by_source(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
"""))
        obj = ListCmd()


    def test_list_groups(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
"""))
        obj = ListCmd()


    def test_list_locations(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
"""))
        obj = ListCmd()


    def test_list_printers(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
"""))
        obj = ListCmd()


    def test_list_flags(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
"""))
        obj = ListCmd()


    def test_list_actions(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
"""))
        obj = ListCmd()


    def test_list_plugins(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        mocker.patch("doot.args", new=ChainGuard.read(
"""
[cmd.args]
"""))
        obj = ListCmd()
