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
from doot._abstract.cmd import Command_i
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
        assert("target" in names)
        assert("help" in names)

    def test_call_bad_cli_args(self, monkeypatch, mocker):
        mocker.patch("doot.args")
        doot.args.cmd.args.target = ""
        doot.args.cmd.args.all = False
        obj = ListCmd()

        with pytest.raises(ValueError):
            obj({}, {})

    def test_call_no_reporter(self, mocker):
        mocker.patch("doot.args")
        doot.args.cmd.args.target = ""
        doot.args.cmd.args.all    = True
        obj = ListCmd()

        with pytest.raises(doot.errors.DootPluginError):
            obj({}, {})

    def test_call_all_empty(self, caplog, mocker):
        mocker.patch("doot.args")
        doot.args.cmd.args.target = ""
        doot.args.cmd.arg.all = True
        obj    = ListCmd()
        obj({}, {"reporter": [mocker.stub("Reporter Stub")]})

        message_set = {x.message for x in caplog.records}
        assert("No Tasks Defined" in message_set)


    def test_call_all_not_empty(self, caplog, mocker):
        mocker.patch("doot.args")
        doot.args.cmd.args.target = ""
        doot.args.cmd.args.all = True
        obj = ListCmd()
        plugin_mock = {"reporter": [mocker.stub("Reporter Stub")]}
        tasker_mock = { "simple" : ({}, type), "other": ({}, type) }
        obj(tasker_mock, plugin_mock)
        message_set : set[str] = {x.message for x in caplog.records}

        assert("Defined Task Generators:" in message_set)
        assert("simple (<class 'type'>) : {}" in message_set)
        assert("other (<class 'type'>) : {}" in message_set)

    def test_call_target_not_empty(self, caplog, mocker):
        mocker.patch("doot.args")
        doot.args.cmd.args.target = "simple"
        doot.args.cmd.args.all = False
        obj = ListCmd()
        plugin_mock = {"reporter": [mocker.stub("Reporter Stub")]}
        tasker_mock = { "simple" : ({}, type), "other": ({}, type) }
        result = obj(tasker_mock, plugin_mock)
        message_set : set[str] = {x.message for x in caplog.records}

        assert("Tasks for Target: simple" in message_set)
        assert("simple (<class 'type'>) : {}" in message_set)


    def test_call_partial_target_not_empty(self, caplog, mocker):
        mocker.patch("doot.args")
        doot.args.cmd.args.target = "simp"
        doot.args.cmd.args.all = False
        obj = ListCmd()
        plugin_mock = {"reporter": [mocker.stub("Reporter Stub")]}
        tasker_mock = { "simple" : ({}, type), "other": ({}, type), "diffSimple": ({}, type) }
        result = obj(tasker_mock, plugin_mock)
        message_set : set[str] = {x.message for x in caplog.records}

        assert("Tasks for Target: simp" in message_set)
        assert("simple (<class 'type'>) : {}" in message_set)
        assert("diffSimple (<class 'type'>) : {}" in message_set)
