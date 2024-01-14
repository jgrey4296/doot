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
from doot.structs import DootTaskSpec, DootCodeReference
from doot._abstract import TaskBase_i

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

mini_ref        = DootCodeReference.from_str("doot.task.base_job:DootJob").add_mixins("doot.mixins.job.mini_builder:MiniBuilderMixin")
MiniBuilder     = mini_ref.try_import()

class SimpleMini(MiniBuilder):

    def _build_subs(self) -> Generator[DootTaskSpec]:
        yield self._build_subtask(0, "first")
        yield self._build_subtask(0, "second")


class TestMiniBuilder:

    def test_initial(self):
        obj = MiniBuilder(DootTaskSpec.from_dict({"name" : "test::basic"}))
        assert(isinstance(obj, TaskBase_i))

    def test_build_no_actions_default(self):
        """
        On its only, a minibuilder just adds actions to the $head$
        """
        obj = SimpleMini(DootTaskSpec.from_dict({"name" : "test::basic",
            # "head_actions": [{"do":"log", "msg":"test_head"}],
        }))
        assert(isinstance(obj, TaskBase_i))
        subtasks = list(obj.build())
        assert(len(subtasks) == 3)
        for task in subtasks:
            assert(task.name.group == "test")
            assert(task.name.task in ["basic.$head$", "basic.first", "basic.second"])
            assert(not bool(task.actions))


    def test_build_actions(self):
        """
        On its only, a minibuilder just adds actions to the $head$
        """
        obj = SimpleMini(DootTaskSpec.from_dict({"name" : "test::basic",
            "sub_actions": [{"do":"log", "msg":"test_sub1"},
                            {"do":"log", "msg":"test_sub2"}],
            "head_actions": [{"do":"log", "msg":"test_head"}],
        }))
        assert(isinstance(obj, TaskBase_i))
        subtasks = list(obj.build())
        assert(len(subtasks) == 3)
        for task in subtasks:
            if (task.name.task == "basic.$head$"):
                assert(len(task.actions) == 1)
            elif (task.name.task in ["basic.first", "basic.second"]):
                assert(len(task.actions) == 2)


    def test_build_actions_with_ctor_name(self):
        """
        On its only, a minibuilder just adds actions to the $head$
        """
        obj = SimpleMini(DootTaskSpec.from_dict({"name" : "test::basic",
            "sub_task": "example::blah",
            "head_task": "example::bloo",
            "sub_actions": [{"do":"log", "msg":"test_sub1"},
                            {"do":"log", "msg":"test_sub2"}],
            "head_actions": [{"do":"log", "msg":"test_head"}],
        }))
        assert(isinstance(obj, TaskBase_i))
        subtasks = list(obj.build())
        assert(len(subtasks) == 3)
        for task in subtasks:
            if (task.name.task == "basic.$head$"):
                assert(len(task.actions) == 1)
                assert(str(task.ctor) == "example::bloo")
            elif (task.name.task in ["basic.first", "basic.second"]):
                assert(len(task.actions) == 2)
                assert(str(task.ctor) == "example::blah")
