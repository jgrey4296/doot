#!/usr/bin/env python3
"""

"""
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings

import pytest

import doot
doot._test_setup()
import doot._abstract
from doot.task.check_locs import CheckLocsTask
from doot.control.locations import DootLocations
from doot.structs import DootTaskSpec
from doot.utils.testing_fixtures import wrap_tmp

logging = logmod.root

class TestCheckLocsTask:

    def test_initial(self):
        obj = CheckLocsTask(DootTaskSpec.build({"name": "basic"}))
        assert(isinstance(obj, doot._abstract.Task_i))

    def test_expand_actions(self):
        pytest.skip("todo")
        obj = CheckLocsTask()
        actions = list(obj.actions)
        assert(len(actions) > 1)
        assert(callable(actions[0]))

    def test_expand_multi_actions(self):
        pytest.skip("todo")
        obj = CheckLocsTask()
        actions = list(obj.actions)
        assert(len(actions) == 2)
        assert(callable(actions[0]))
        assert(callable(actions[1]))

    def test_run_action(self):
        pytest.skip("todo")
        obj = CheckLocsTask()
        actions = list(obj.actions)
        assert(len(actions) == 1)
        result = actions[0]({})
        assert(result is True)

    def test_run_action_nonexistent_target(self):
        pytest.skip("todo")
        obj = CheckLocsTask()
        actions = list(obj.actions)
        assert(len(actions) == 1)
        result = actions[0]({})
        assert(result is False)
