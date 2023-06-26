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

    @pytest.fixture(scope="function")
    def setup(self):
        self.val = 5

    @pytest.fixture(scope="function")
    def cleanup(self):
        yield
        assert(self.val == 5)
        self.val = None

    def test_initial(self):
        obj = ListCmd()
        assert(isinstance(obj, Command_i))

    def test_param_specs(self):
        obj = ListCmd()
        result = obj.param_specs
        assert(isinstance(result, list))
        names = [x.name for x in result]
        assert("all" in names)
        assert("dependencies"in names)
        assert("target" in names)


    def test_call_bad_cli_args(self, monkeypatch, mocker):
        mocker.patch("doot.args")
        doot.args.cmd.target = ""
        doot.args.cmd.all = False
        obj = ListCmd()

        with pytest.raises(ValueError):
            obj({}, {})

    def test_call_no_reporter(self, mocker):
        mocker.patch("doot.args")
        doot.args.cmd.target = ""
        doot.args.cmd.all    = True
        obj = ListCmd()

        with pytest.raises(doot.errors.DootPluginError):
            obj({}, {})


    def test_call_empty(self, caplog, mocker):
        mocker.patch("doot.args")
        doot.args.cmd.target = ""
        doot.args.cmd.all = True
        obj    = ListCmd()
        obj({}, {"reporter": [mocker.stub("Reporter Stub")]})

        for record in caplog.records:
            if "No Tasks Defined" in record.message:
                return

        assert(False), "Messages should have been found"


    def test_call_not_empty(self, caplog, mocker):
        mocker.patch("doot.args")
        doot.args.cmd.target = ""
        doot.args.cmd.all = True
        obj = ListCmd()
