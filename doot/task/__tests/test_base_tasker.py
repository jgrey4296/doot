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

logging = logmod.root

import doot
from doot.enums import TaskFlags
from doot.structs import DootTaskSpec, TaskStub
from doot.task.base_tasker import DootTasker
import doot._abstract

# caplog
# mocker.patch | patch.object | patch.multiple | patch.dict | stopall | stop | spy | stub
# pytest.mark.filterwarnings
# pytest.parameterize
# pytest.skip | skipif | xfail
# with pytest.deprecated_call
# with pytest.raises
# with pytest.warns(warntype)

class TestBaseTasker:

    def test_initial(self):
        tasker = DootTasker(DootTaskSpec.from_dict({"name": "basic::example", "flags": ["TASKER"]}))
        assert(isinstance(tasker, doot._abstract.TaskBase_i))
        assert(TaskFlags.TASKER in tasker.spec.flags)


    def test_paramspecs(self):
        tasker = DootTasker(DootTaskSpec.from_dict({"name": "basic::example"}))
        param_specs = tasker.param_specs
        assert(isinstance(param_specs, list))
        assert(len(param_specs) == 3)


    def test_spec(self):
        ##-- setup
        tasker1 = DootTasker(DootTaskSpec.from_dict({"name" :"basic::example"}))
        tasker2 = DootTasker(DootTaskSpec.from_dict({"name" :"other.group::blah"}))
        ##-- end setup
        assert(str(tasker1.name) == "basic::example")
        assert(str(tasker2.name) == "\"other.group\"::blah")
        assert(tasker1 != tasker2)
        assert(tasker1 == tasker1)


    def test_build(self):
        ##-- setup
        tasker = DootTasker(DootTaskSpec.from_dict({"name": "basic::example"}))
        ##-- end setup

        # Run:
        tasks = list(tasker.build())

        ##-- check
        assert(len(tasks) == 1)
        ##-- end check
        pass


    def test_build_multi(self):
        ##-- setup
        tasker = DootTasker(DootTaskSpec.from_dict({"name": "basic::example"}))
        ##-- end setup

        # Run:
        tasks = list(tasker.build())

        ##-- check
        assert(len(tasks) == 1)
        ##-- end check
        pass


    def test_class_stub(self):
        stub_obj = TaskStub(ctor=DootTasker)
        stub = DootTasker.stub_class(stub_obj)
        assert(isinstance(stub, TaskStub))
