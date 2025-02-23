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
import doot
doot._test_setup()

from doot.control.overlord import DootOverlord

class TestOverlord:

    def test_initial(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        mocker.patch("doot.loaders.task_loader.DootTaskLoader")
        overlord = DootOverlord()
        assert(bool(overlord))
        assert(overlord.args == ["doot"])

    def test_plugins_loaded(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        mocker.patch("doot.loaders.task_loader.DootTaskLoader")
        overlord = DootOverlord()
        overlord._load_plugins()
        assert(bool(overlord.plugins))
        assert(all(x in overlord.plugins for x in doot.aliases.keys()))

    def test_cmds_loaded(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        mocker.patch("doot.loaders.task_loader.DootTaskLoader")
        overlord = DootOverlord()
        overlord._load_plugins()
        overlord._load_commands()
        assert(bool(overlord.cmds))
        assert(len(overlord.cmds) >= len(doot.aliases.command))

    def test_tasks_loaded(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        mocker.patch("doot.loaders.task_loader.task_sources")
        overlord = DootOverlord(
            extra_config={"tasks" : {"basic" : [{"name": "simple"}]}}
        )
        overlord._load_plugins()
        overlord._load_commands()
        overlord._load_tasks(overlord._extra_config)
        assert(bool(overlord.tasks))

    def test_tasks_multi(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        mocker.patch("doot.loaders.task_loader.task_sources")
        mocker.patch("doot._configs_loaded_from")
        overlord = DootOverlord(extra_config={
            "tasks" : {"basic": [
                {"name": "simple"},
                {"name": "another"},
            ]}})
        overlord.setup()
        assert(bool(overlord.tasks))
        assert(len(overlord.tasks) == 2), len(overlord.tasks)


    @pytest.mark.skip
    def test_todo(self):
        pass
