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
import functools as ftz

import pytest
logging = logmod.root

import tomlguard
import doot
import doot.constants
from doot.structs import DootTaskSpec, TaskStub
from doot.task.base_task import DootTask
import doot._abstract

##-- reminder
# caplog
# mocker.patch | patch.object | patch.multiple | patch.dict | stopall | stop | spy | stub
# pytest.mark.filterwarnings
# pytest.parameterize
# pytest.skip | skipif | xfail
# with pytest.deprecated_call
# with pytest.raises
# with pytest.warns(warntype)

##-- end reminder

basic_action = lambda x: ftz.partial(lambda val, state: logging.info("Got: %s : %s", val, state), x)

class TestBaseTask:

    def test_initial(self):
        task = DootTask(DootTaskSpec(name="basic::example"), job=None)
        assert(isinstance(task, doot._abstract.Task_i))


    def test_lambda_action(self):
        task         = DootTask(DootTaskSpec.from_dict({"name":"basic::example", "action_ctor":basic_action}), job=None)
        assert(isinstance(task, doot._abstract.Task_i))


    def test_expand_lambda_action(self):
        task                = DootTask(DootTaskSpec.from_dict({"name":"basic::example", "action_ctor":basic_action, "actions": [{"do": "doot.actions.base_action:DootBaseAction", "args":["blah"]}]}), job=None)
        actions             = list(task.actions)
        assert(len(actions) == 1)


    def test_run_lambda_action(self, caplog):
        caplog.set_level("DEBUG", logger="doot._printer")
        task         = DootTask(DootTaskSpec.from_dict({"name":"basic::example", "action_ctor":basic_action, "actions": [{"do": "doot.actions.base_action:DootBaseAction", "args":["blah"]}]}), job=None)
        actions      = list(task.actions)
        result       = actions[0]({"example": "state"})
        assert(result == {"count": 1})
        assert("Base Action Called: 0" in caplog.messages)
        assert("blah" in caplog.messages)


    def test_expand_action_str(self, caplog):
        caplog.set_level("DEBUG", logger="doot._printer")
        task         = DootTask(DootTaskSpec.from_dict({"name":"basic::example", "action_ctor": "test_base_task:basic_action", "actions": [{"do": "doot.actions.base_action:DootBaseAction", "args":["blah"]}]}), job=None)
        actions      = list(task.actions)
        result       = actions[0]({"example": "state"})
        assert(result == {"count" : 1})
        assert("Base Action Called: 0" in caplog.messages)

    def test_toml_class_stub(self):
        """ build the simplest stub from the class itself """
        stub_obj = TaskStub(ctor=DootTask)
        stub     = DootTask.stub_class(stub_obj)
        assert(str(stub['name'].default) == doot.constants.DEFAULT_STUB_TASK_NAME)

    def test_toml_instance_stub(self):
        """ build the next simplest stub from an instance of the task """
        stub_obj = TaskStub(ctor=DootTask)
        task     = DootTask(DootTaskSpec.from_dict({"name" : "basic::example", "flags" : ["TASK", "IDEMPOTENT"]}), job=None)
        stub     = task.stub_instance(stub_obj)
        assert(str(stub['name'].default) == "basic::example")
        as_str = stub.to_toml()

    def test_toml_instance_stub_rebuild(self):
        """ take a stub and turn it into a task spec  """
        stub_obj         = TaskStub(ctor=DootTask)
        task             = DootTask(DootTaskSpec.from_dict({"name" : "basic::example", "flags" : ["TASK", "IDEMPOTENT"]}), job=None)
        stub             = task.stub_instance(stub_obj)
        as_str           = stub.to_toml()
        loaded           = tomlguard.read(as_str)
        as_dict          = dict(loaded.tasks.basic[0])
        as_dict['group'] = "basic"
        new_spec         = DootTaskSpec.from_dict(as_dict)
        assert(isinstance(new_spec, DootTaskSpec))
        assert(str(new_spec.name) == str(task.spec.name))
