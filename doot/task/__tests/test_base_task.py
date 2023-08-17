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

import tomler
import doot
import doot.constants
from doot.structs import DootTaskSpec
from doot.task.base_task import DootTask
import doot._abstract

# caplog
# mocker.patch | patch.object | patch.multiple | patch.dict | stopall | stop | spy | stub
# pytest.mark.filterwarnings
# pytest.parameterize
# pytest.skip | skipif | xfail
# with pytest.deprecated_call
# with pytest.raises
# with pytest.warns(warntype)

class TestBaseTask:

    @pytest.fixture(scope="function")
    def setup(self):
        pass

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass

    def test_initial(self):
        task = DootTask(DootTaskSpec(name="basic::example"), tasker=None)
        assert(isinstance(task, doot._abstract.Task_i))

    def test_toml_class_stub(self):
        """ build the simplest stub from the class itself """
        stub   = DootTask.stub_class()
        assert(str(stub['name'].default) == doot.constants.DEFAULT_STUB_TASK_NAME)

    def test_toml_instance_stub(self):
        """ build the next simplest stub from an instance of the task """
        ##-- setup
        task   = DootTask(DootTaskSpec.from_dict({"name" : "basic::example", "flags" : ["TASK", "IDEMPOTENT"]}), tasker=None)
        ##-- end setup
        stub   = task.stub_instance()
        assert(str(stub['name'].default) == "basic::example")
        as_str = stub.to_toml()

    def test_toml_instance_stub_rebuild(self):
        """ take a stub and turn it into a task spec  """
        ##-- setup
        task   = DootTask(DootTaskSpec.from_dict({"name" : "basic::example", "flags" : ["TASK", "IDEMPOTENT"]}), tasker=None)
        ##-- end setup
        stub   = task.stub_instance()
        as_str = stub.to_toml()
        loaded = tomler.read(as_str)
        as_dict  = dict(loaded.tasks.basic[0])
        as_dict['group'] = "basic"
        new_spec = DootTaskSpec.from_dict(as_dict)
        assert(isinstance(new_spec, DootTaskSpec))
        assert(str(new_spec.name) == str(task.spec.name))
