#!/usr/bin/env python3
"""

"""
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
from dataclasses import fields
import warnings
import os

logging = logmod.root

import pytest

import doot
doot._test_setup()

import doot._abstract
from doot.structs import TaskName, ActionSpec
from doot._abstract.task import Action_p
from doot.task.base_task import DootTask
from doot.actions.base_action import DootBaseAction
from doot.actions import postbox as pb

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

class TestInternalPostBox:

    @pytest.fixture(scope="function")
    def setup(self):
        pb._DootPostBox.clear()

    def test_initial(self):
        action = pb.PutPostAction()
        assert(isinstance(action, Action_p))

    def test_clear(self, setup):
        assert(not bool(pb._DootPostBox.boxes))
        pb._DootPostBox.boxes['test']['-'].append(1)
        assert(bool(pb._DootPostBox.boxes))
        pb._DootPostBox.clear()
        assert(not bool(pb._DootPostBox.boxes))

    def test_put(self, setup):
        key = TaskName.build("simple::test..key")
        assert(not bool(pb._DootPostBox.boxes))
        pb._DootPostBox.put(key, 1)
        assert(bool(pb._DootPostBox.boxes))
        assert(pb._DootPostBox.boxes['simple::test']['key'] == [1])

    def test_multi_put(self, setup):
        key = TaskName.build("simple::test..key")
        assert(not bool(pb._DootPostBox.boxes))
        pb._DootPostBox.put(key, 1)
        assert(bool(pb._DootPostBox.boxes))
        assert(pb._DootPostBox.boxes['simple::test']['key'] == [1])
        pb._DootPostBox.put(key, 2)
        assert(pb._DootPostBox.boxes['simple::test']['key'] == [1, 2])

    def test_put_list(self, setup):
        key = TaskName.build("simple::test..key")
        assert(not bool(pb._DootPostBox.boxes))
        pb._DootPostBox.put(key, [1,2,3,4])
        pb._DootPostBox.put(key, 5)
        assert(bool(pb._DootPostBox.boxes))
        assert(pb._DootPostBox.boxes['simple::test']['key'] == [1,2,3,4,5])

    def test_get(self, setup):
        key = TaskName.build("simple::test..key")
        pb._DootPostBox.put(key, [1,2,3,4])
        result = pb._DootPostBox.get(key)
        assert(result == [1,2,3,4])

    def test_box_separation(self, setup):
        key1 = TaskName.build("simple::test..key")
        key2 = TaskName.build("simple::other..key")
        pb._DootPostBox.put(key1, [1,2,3,4])
        pb._DootPostBox.put(key2, ["a","b","c","d"])
        assert(pb._DootPostBox.get(key1) == [1,2,3,4])
        assert(pb._DootPostBox.get(key2) == ["a","b","c","d"])

    def test_box_result_independence(self, setup):
        key1 = TaskName.build("simple::test..key")
        pb._DootPostBox.put(key1, [1,2,3,4])
        result1 = pb._DootPostBox.get(key1)
        pb._DootPostBox.put(key1, 5)
        result2 = pb._DootPostBox.get(key1)
        assert(result1 == [1,2,3,4])
        assert(result2 == [1,2,3,4,5])

    def test_get_whole_box(self, setup):
        key1 = TaskName.build("simple::test..key")
        key2 = TaskName.build("simple::test..other")
        pb._DootPostBox.put(key1, [1,2,3,4])
        pb._DootPostBox.put(key2, "a")
        result = pb._DootPostBox.get(TaskName.build("simple::test..*"))
        assert(isinstance(result, dict))
        assert("key" in result)
        assert("other" in result)

    def test_put_key_no_subkey(self, setup):
        key1 = TaskName.build("simple::test")

        with pytest.raises(ValueError):
            pb._DootPostBox.put(key1, [1,2,3,4])

    def test_get_key_no_subkey(self, setup):
        key1 = TaskName.build("simple::test")

        with pytest.raises(ValueError):
            pb._DootPostBox.get(key1)

    def test_put_empty_value_nop(self, setup):
        key1 = TaskName.build("simple::test..box")
        assert(not bool(pb._DootPostBox.boxes))
        pb._DootPostBox.put(key1, None)
        assert(not bool(pb._DootPostBox.boxes))
        pb._DootPostBox.put(key1, [])
        assert(not bool(pb._DootPostBox.boxes))
        pb._DootPostBox.put(key1, {})
        assert(not bool(pb._DootPostBox.boxes))

class TestPutAction:

    @pytest.fixture(scope="function")
    def setup(self):
        pb._DootPostBox.clear()

    @pytest.fixture(scope="function")
    def spec_implicit(self, mocker):
        """ an implicit box target """
        return ActionSpec.build({"do":None, "args":[], "specific_box":"{aval}"})

    @pytest.fixture(scope="function")
    def spec_explicit(self, mocker):
        """ an explicit box target """
        return ActionSpec.build({"do":None, "args":[], "simple::other.task..specific_box":"{aval}"})

    @pytest.fixture(scope="function")
    def state(self, mocker):
        return {"aval":[1,2,3,4]}

    def test_implicit_task(self, setup, spec_implicit, state):
        """
        Expands 'aval' into [1,2,3,4],
        adds it to 'simple::task..specific_box
        """
        assert(not bool(pb._DootPostBox.boxes))
        state['_task_name'] = TaskName.build("simple::task..<UUID>")
        action = pb.PutPostAction()
        action(spec_implicit, state)
        assert(bool(pb._DootPostBox.boxes))
        assert('specific_box' in pb._DootPostBox.boxes['simple::task'])
        assert(pb._DootPostBox.boxes['simple::task']['specific_box'] == [1,2,3,4])

    def test_args_go_to_default_subbox(self, setup, spec_implicit, state):
        """
        Expands 'aval' into [1,2,3,4],
        Note that 'args' is *only* useable for expansionsc
        adds it to 'simple::task..specific_box
        """
        assert(not bool(pb._DootPostBox.boxes))
        state['_task_name'] = TaskName.build("simple::task..<UUID>")
        spec_implicit.args = ["{aval}"]
        action = pb.PutPostAction()
        action(spec_implicit, state)
        assert(bool(pb._DootPostBox.boxes))
        assert('specific_box' in pb._DootPostBox.boxes['simple::task'])
        assert(pb._DootPostBox.boxes['simple::task']['specific_box'] == [1,2,3,4])
        assert(pb._DootPostBox.boxes['simple::task']['-'] == [1,2,3,4])

    def test_args_must_be_expansions(self, setup, spec_implicit, state):
        """
        Note that 'args' is *only* useable for expansions
        So "a", "b" and "c" will all expand to nothing,
        and nothing will be added to the default subbox
        """
        assert(not bool(pb._DootPostBox.boxes))
        state['_task_name'] = TaskName.build("simple::task..<UUID>")
        spec_implicit.args = ["a", "b", "c"]
        action = pb.PutPostAction()
        action(spec_implicit, state)
        assert(bool(pb._DootPostBox.boxes))
        assert('specific_box' in pb._DootPostBox.boxes['simple::task'])
        assert(pb._DootPostBox.boxes['simple::task']['specific_box'] == [1,2,3,4])
        assert('-' not in pb._DootPostBox.boxes['simple::task'])

    def test_explicit_task(self, setup, spec_explicit, state):
        """
        Expands 'aval' into [1,2,3,4],
        adds it to the explicitly tasked key 'simple::other.task..specific_box
        """
        assert(not bool(pb._DootPostBox.boxes))
        state['_task_name'] = TaskName.build("simple::task..<UUID>")

        action = pb.PutPostAction()
        action(spec_explicit, state)
        assert(bool(pb._DootPostBox.boxes))
        assert('specific_box' in pb._DootPostBox.boxes['simple::other.task'])
        assert(pb._DootPostBox.boxes['simple::other.task']['specific_box'] == [1,2,3,4])

class TestGetAction:

    @pytest.fixture(scope="function")
    def setup(self):
        pb._DootPostBox.clear()
        pb._DootPostBox.put(TaskName.build("simple::task..key"), ["a","b","c","d"])

    @pytest.fixture(scope="function")
    def spec_explicit(self, mocker):
        return ActionSpec.build({"do":None, "args":[], "res_key":"simple::task..key"})

    @pytest.fixture(scope="function")
    def spec_implicit(self, mocker):
        return ActionSpec.build({"do":None, "args":[], "res_key":"key"})

    @pytest.fixture(scope="function")
    def state(self, mocker):
        return {"aval":[1,2,3,4]}

    def test_explicit(self, setup, spec_explicit, state):
        """
        Gets the value from the postbox, at 'simple::task..key'
        and returns a state update dict binding the value to 'res_key'
        """
        action = pb.GetPostAction()
        result = action(spec_explicit, state)
        assert(isinstance(result, dict))
        assert(result['res_key'] == ["a", "b", "c", "d"])

    def test_implicit_fail(self, setup, spec_implicit, state):
        """
        Gets the value from the postbox, at 'simple::task..key'
        and returns a state update dict binding the value to 'res_key'
        """
        action = pb.GetPostAction()
        with pytest.raises(ValueError):
            action(spec_implicit, state)
