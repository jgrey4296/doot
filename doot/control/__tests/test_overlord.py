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
import sys
import tomler
import doot
doot.config = tomler.Tomler({})
from doot.control.overlord import DootOverlord

class TestOverlord:

    @mock.patch.object(sys, "argv", ["doot"])
    def test_initial(self):
        overlord = DootOverlord()
        assert(bool(overlord))
        assert(overlord.args == ["doot"])

    @mock.patch.object(sys, "argv", ["doot"])
    def test_plugins_loaded(self):
        overlord = DootOverlord()
        assert(bool(overlord.plugins))
        assert(all(x in overlord.plugins for x in doot.constants.DEFAULT_PLUGINS.keys()))

    @mock.patch.object(sys, "argv", ["doot"])
    def test_cmds_loaded(self):
        overlord = DootOverlord()
        assert(bool(overlord.cmds))
        assert(len(overlord.cmds) == len(doot.constants.DEFAULT_PLUGINS['command']))

    @mock.patch.object(sys, "argv", ["doot"])
    def test_taskers_loaded(self):
        overlord = DootOverlord(
            extra_config={"tasks" : {"basic" : [{"name": "simple", "type": "basic"}]}}
        )
        assert(bool(overlord.taskers))

    @mock.patch.object(sys, "argv", ["doot"])
    def test_taskers_multi(self):
        overlord = DootOverlord(extra_config={
            "tasks" : {"basic": [
                {"name": "simple", "type": "basic"},
                {"name": "another", "type": "basic"}
        ]}})
        assert(bool(overlord.taskers))
        assert(len(overlord.taskers) == 2)

    @mock.patch.object(sys, "argv", ["doot"])
    def test_taskers_name_conflict(self):
        with pytest.raises(ResourceWarning):
            DootOverlord(extra_config={
                "tasks" : {"basic" : [
                    {"name": "simple", "type": "basic"},
                    {"name": "simple", "type": "basic"}
            ]}})

    @mock.patch.object(sys, "argv", ["doot"])
    def test_taskers_bad_type(self):
        with pytest.raises(ResourceWarning):
            DootOverlord(extra_config={"tasks" : {"basic": [{"name": "simple", "type": "not_basic"}]}})
