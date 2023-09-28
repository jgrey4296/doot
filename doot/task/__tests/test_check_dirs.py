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
import doot._abstract
from doot.task.check_dirs import CheckDirTasker, CheckDirTask
from doot.control.locations import DootLocations
from doot.structs import DootTaskSpec
from doot.utils.testing_fixtures import wrap_tmp


logging = logmod.root

##-- pytest reminder
# caplog
# mocker.patch | patch.object | patch.multiple | patch.dict | stopall | stop | spy | stub
# pytest.mark.filterwarnings
# pytest.parameterize
# pytest.skip | skipif | xfail
# with pytest.deprecated_call
# with pytest.raises
# with pytest.warns(warntype)

##-- end pytest reminder

class TestCheckDir:


    def test_initial(self):
        obj = CheckDirTasker()
        assert(isinstance(obj, doot._abstract.Tasker_i))


    def test_expansion(self):
        locs  = DootLocations(pl.Path())
        obj   = CheckDirTasker(locs)
        tasks = list(obj.build())
        assert(len(tasks) == 1)


    def test_multi_expansion(self):
        locs  = DootLocations(pl.Path())
        locs.update({"test": "blah"})
        obj   = CheckDirTasker(locs)
        tasks = list(obj.build())
        assert(len(tasks) == 2)


    def test_multi_expansion_2(self):
        locs  = DootLocations(pl.Path())
        locs.update({"test": "blah", "bloo": "blee"})
        obj   = CheckDirTasker(locs)
        tasks = list(obj.build())
        assert(len(tasks) == 3)



class TestCheckDirTask:

    def test_initial(self):
        obj = CheckDirTask(DootTaskSpec.from_dict({"name": "basic"}))
        assert(isinstance(obj, doot._abstract.Task_i))


    def test_expand_actions(self):
        obj = CheckDirTask(DootTaskSpec.from_dict({"name": "basic", "actions": [[pl.Path()]]}))
        actions = list(obj.actions)
        assert(len(actions) == 1)
        assert(callable(actions[0]))


    def test_expand_multi_actions(self):
        obj = CheckDirTask(DootTaskSpec.from_dict({"name": "basic", "actions": [[pl.Path()], [pl.Path("blah")]]}))
        actions = list(obj.actions)
        assert(len(actions) == 2)
        assert(callable(actions[0]))
        assert(callable(actions[1]))


    def test_run_action(self):
        obj = CheckDirTask(DootTaskSpec.from_dict({"name": "basic", "actions": [[pl.Path()]]}))
        actions = list(obj.actions)
        assert(len(actions) == 1)
        result = actions[0]({})
        assert(result is True)


    def test_run_action_nonexistent_target(self):
        obj = CheckDirTask(DootTaskSpec.from_dict({"name": "basic", "actions": [[pl.Path("blah")]]}))
        actions = list(obj.actions)
        assert(len(actions) == 1)
        result = actions[0]({})
        assert(result is False)
