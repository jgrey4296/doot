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
import functools as ftz
import sys
import io
import contextlib
import doot
import doot.errors
from doot._abstract import Command_i
from doot.structs import DootTaskSpec
from doot.cmds.list_cmd import ListCmd

class TestListCmd:

    def test_initial(self):
        obj = ListCmd()
        assert(isinstance(obj, Command_i))

    def test_param_specs(self):
        obj    = ListCmd()
        result = obj.param_specs
        assert(isinstance(result, list))
        names = [x.name for x in result]
        assert("all" in names)
        assert("dependencies"in names)
        assert("pattern" in names)
        assert("help" in names)

    def test_call_bad_cli_args(self, monkeypatch, mocker):
        mock_obj                     = mocker.patch("doot.args")
        doot.args.tasks              = []
        doot.args.cmd.args.pattern   = ""
        doot.args.cmd.args.all       = False
        doot.args.cmd.args.by_source = False
        obj = ListCmd()

        with pytest.raises(doot.errors.DootError):
            obj({}, {})

    def test_call_all_empty(self, caplog, mocker):
        mocker.patch("doot.args")
        doot.args.cmd.args.pattern = ""
        doot.args.cmd.arg.all      = True
        obj    = ListCmd()
        obj({}, {"reporter": [mocker.stub("Reporter Stub")]})

        message_set = {x.message for x in caplog.records}
        assert("No Tasks Defined" in message_set)


    def test_call_all_not_empty(self, caplog, mocker):
        mocker.patch("doot.args")
        del doot.args.cmd.args.keys
        doot.args.cmd.args.__iter__.return_value = iter([("pattern", ""), ("all", True)])
        doot.args.cmd.args.pattern = ""
        doot.args.cmd.args.all     = True

        obj = ListCmd()
        mock_class1 = mocker.MagicMock(type)
        mock_class1.__module__ = "builtins"
        mock_class1.__name__   = "type"
        mock_class2 = mocker.MagicMock(type)
        mock_class2.__module__ = "builtins"
        mock_class2.__name__   = "other.type"
        plugin_mock = {"reporter": [mocker.stub("Reporter Stub")]}
        job_mock = {
            "simple" : DootTaskSpec.from_dict({"group": "blah", "name": "simple", "ctor": mock_class1}),
            "other"  : DootTaskSpec.from_dict({"group": "bloo", "name": "other", "ctor": mock_class2})
            }
        obj(job_mock, plugin_mock)
        message_set : set[str] = {x.message.lower().strip() for x in caplog.records}

        assert("defined task generators by group:" in message_set)
        assert(any(x.startswith("simple :: ") for x in message_set) )
        assert(any(x.startswith("other  :: ") for x in message_set) )

    def test_call_target_not_empty(self, caplog, mocker):
        mocker.patch("doot.args")
        del doot.args.cmd.args.keys
        doot.args.cmd.args.__iter__.return_value = iter([("pattern", "simple"), ("all", False)])
        doot.args.cmd.args.pattern = "simple"
        doot.args.cmd.args.all     = False
        obj = ListCmd()
        plugin_mock  = {"reporter": [mocker.stub("Reporter Stub")]}
        job_mock = {
                       "simple" : DootTaskSpec.from_dict({"group": "blah", "name": "simple"}),
                       "other"  : DootTaskSpec.from_dict({"group": "bloo", "name": "other"}),
            }
        result = obj(job_mock, plugin_mock)
        message_set : set[str] = {x.message.lower().strip() for x in caplog.records}

        assert("tasks for pattern: simple" in message_set)
        assert( any(x.startswith("blah::simple :: doot.task.base_job:dootjob") for x in message_set) )


    def test_call_partial_target_not_empty(self, caplog, mocker):
        mocker.patch("doot.args")
        del doot.args.cmd.args.keys
        doot.args.cmd.args.__iter__.return_value = iter([("pattern", "simp"), ("all", False)])
        doot.args.cmd.args.pattern = "simp"
        doot.args.cmd.args.all     = False
        obj = ListCmd()
        plugin_mock = {"reporter": [mocker.stub("Reporter Stub")]}
        job_mock = { "blah::simple" : DootTaskSpec.from_dict({"group": "blah", "name": "simple"}),
                        "bloo::other": DootTaskSpec.from_dict({"group": "bloo", "name": "other"}),
                        "bloo::diffSimple": DootTaskSpec.from_dict({"group": "bloo", "name": "diffSimple"}),
                       }
        result = obj(job_mock, plugin_mock)
        message_set : set[str] = {x.message.lower().strip() for x in caplog.records}

        assert("tasks for pattern: simp" in message_set)
        assert( any(x.startswith("blah::simple     :: doot.task.base_job:dootjob") for x in message_set) )
        assert( any(x.startswith("bloo::diffsimple :: doot.task.base_job:dootjob") for x in message_set) )
