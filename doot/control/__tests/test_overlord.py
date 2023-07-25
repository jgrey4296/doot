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
##-- end imports
logging = logmod.root

import pytest
import sys
import tomler
import doot
doot.config = tomler.Tomler({})
from doot.control.overlord import DootOverlord

class TestOverlord:

    def test_initial(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        overlord = DootOverlord()
        assert(bool(overlord))
        assert(overlord.args == ["doot"])

    def test_plugins_loaded(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        overlord = DootOverlord()
        assert(bool(overlord.plugins))
        assert(all(x in overlord.plugins for x in doot.constants.DEFAULT_PLUGINS.keys()))

    def test_cmds_loaded(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        overlord = DootOverlord()
        assert(bool(overlord.cmds))
        assert(len(overlord.cmds) == len(doot.constants.DEFAULT_PLUGINS['command']))

    def test_taskers_loaded(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        mocker.patch("doot.loaders.task_loader.task_path")
        overlord = DootOverlord(
            extra_config={"tasks" : {"basic" : [{"name": "simple", "type": "basic"}]}}
        )
        assert(bool(overlord.taskers))

    def test_taskers_multi(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        mocker.patch("doot.loaders.task_loader.task_path")
        mocker.patch("doot._configs_loaded_from")
        overlord = DootOverlord(extra_config={
            "tasks" : {"basic": [
                {"name": "simple", "type": "basic"},
                {"name": "another", "type": "basic"}
        ]}})
        assert(bool(overlord.taskers))
        assert(len(overlord.taskers) == 2), len(overlord.taskers)

    def test_taskers_name_conflict(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        with pytest.raises(doot.errors.DootTaskLoadError):
            DootOverlord(extra_config={
                "tasks" : {"basic" : [
                    {"name": "simple", "type": "basic"},
                    {"name": "simple", "type": "basic"}
            ]}})

    def test_taskers_bad_type(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        with pytest.raises(doot.errors.DootTaskLoadError):
            DootOverlord(extra_config={"tasks" : {"basic": [{"name": "simple", "type": "not_basic"}]}})
