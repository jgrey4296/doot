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
import tomlguard
import doot
doot.config = tomlguard.TomlGuard({})
from doot.control.overlord import DootOverlord

BASIC_JOB_NAME = "job"

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
        assert(bool(overlord.plugins))
        assert(all(x in overlord.plugins for x in doot.constants.DEFAULT_PLUGINS.keys()))

    def test_cmds_loaded(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        mocker.patch("doot.loaders.task_loader.DootTaskLoader")
        overlord = DootOverlord()
        assert(bool(overlord.cmds))
        assert(len(overlord.cmds) >= len(doot.constants.DEFAULT_PLUGINS['command']))

    def test_tasks_loaded(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        mocker.patch("doot.loaders.task_loader.task_sources")
        overlord = DootOverlord(
            extra_config={"tasks" : {"basic" : [{"name": "simple", "ctor": BASIC_JOB_NAME}]}}
        )
        assert(bool(overlord.tasks))

    def test_tasks_multi(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        mocker.patch("doot.loaders.task_loader.task_sources")
        mocker.patch("doot._configs_loaded_from")
        overlord = DootOverlord(extra_config={
            "tasks" : {"basic": [
                {"name": "simple", "ctor": BASIC_JOB_NAME},
                {"name": "another", "ctor": BASIC_JOB_NAME}
        ]}})
        assert(bool(overlord.tasks))
        assert(len(overlord.tasks) == 2), len(overlord.tasks)

    def test_tasks_name_conflict(self, mocker, caplog):
        mocker.patch("sys.argv", ["doot"])
        DootOverlord(extra_config={
            "tasks" : {"basic" : [
                {"name": "simple", "ctor": BASIC_JOB_NAME},
                {"name": "simple", "ctor": BASIC_JOB_NAME}
                ]}})

        assert(f"Overloading Task: basic::simple : {BASIC_JOB_NAME}" in caplog.messages)


    @pytest.mark.skip
    def test_tasks_bad_type(self, mocker):
        mocker.patch("sys.argv", ["doot"])
        with pytest.raises(doot.errors.DootTaskLoadError):
            DootOverlord(extra_config={"tasks" : {"basic": [{"name": "simple", "ctor": "not_basic"}]}})
