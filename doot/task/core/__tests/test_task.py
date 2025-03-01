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

from jgdv.structs.chainguard import ChainGuard
import pytest
logging = logmod.root

import doot
from doot.structs import TaskSpec, TaskStub
from doot.task.core.task import DootTask
import doot._abstract

printer = doot.subprinter()
printer.propagate = True
basic_action = lambda x: ftz.partial(lambda val, state: logging.info("Got: %s : %s", val, state), x)

class TestBaseTask:

    def test_initial(self):
        spec = TaskSpec(name="basic::example")
        match DootTask(spec, job=None):
            case doot._abstract.Task_p():
                assert(True)
            case x:
                 assert(False), x

    def test_lambda_action(self):
        spec = TaskSpec.build({"name":"basic::example", "action_ctor":basic_action})
        match DootTask(spec, job=None):
            case doot._abstract.Task_p():
                assert(True)
            case x:
                 assert(False), x

    def test_expand_lambda_action(self):
        spec = TaskSpec.build({"name":"basic::example",
                               "action_ctor":basic_action,
                               "actions": [{"do": "doot.actions.core.action:DootBaseAction", "args":["blah"]}]})
        match DootTask(spec, job=None):
            case doot._abstract.Task_p() as task:
                actions = list(task.get_action_group("actions"))
                assert(len(actions) == 1)
            case x:
                 assert(False), x

    def test_run_lambda_action(self, caplog):
        caplog.clear()
        caplog.set_level(logmod.NOTSET, logger=printer.name)
        printer.propagate = True
        spec = TaskSpec.build({"name":"basic::example", "action_ctor":basic_action, "actions": [{"do": "doot.actions.core.action:DootBaseAction", "args":["blah"]}]})
        match DootTask(spec, job=None):
            case doot._abstract.Task_p() as task:
                actions = list(task.get_action_group("actions"))
                result = actions[0]({"example": "state"})
                assert(result == {"count": 1})
                assert("Base Action Called: 0" in caplog.messages)
                assert("blah" in caplog.messages)
            case x:
                 assert(False), x

    def test_expand_action_str(self, caplog):
        caplog.set_level("DEBUG", logger=printer.name)
        spec = TaskSpec.build({"name":"basic::example", "action_ctor": "test_base_task:basic_action", "actions": [{"do": "doot.actions.core.action:DootBaseAction", "args":["blah"]}]})
        match DootTask(spec, job=None):
            case doot._abstract.Task_p() as task:
                actions      = task.get_action_group("actions")
                result       = actions[0]({"example": "state"})
                assert(result == {"count" : 1})
                assert("Base Action Called: 0" in caplog.messages)
            case x:
                 assert(False), x

    def test_toml_class_stub(self):
        """ build the simplest stub from the class itself """
        stub_obj = TaskStub(ctor=DootTask)
        stub     = DootTask.stub_class(stub_obj)
        assert(str(stub['name'].default) == doot.constants.names.DEFAULT_STUB_TASK_NAME)

    def test_toml_instance_stub(self):
        """ build the next simplest stub from an instance of the task """
        stub_obj = TaskStub(ctor=DootTask)
        task     = DootTask(TaskSpec.build({"name" : "basic::example", "flags" : ["TASK", "IDEMPOTENT"]}), job=None)
        stub     = task.stub_instance(stub_obj)
        assert(str(stub['name'].default) == "basic::example")
        as_str = stub.to_toml()

    def test_toml_instance_stub_rebuild(self):
        """ take a stub and turn it into a task spec  """
        stub_obj         = TaskStub(ctor=DootTask)
        task             = DootTask(TaskSpec.build({"name" : "basic::example",
                                                    "flags" : ["TASK", "IDEMPOTENT"]}), job=None)
        stub             = task.stub_instance(stub_obj)
        as_str           = stub.to_toml()
        loaded           = ChainGuard.read(as_str)
        as_dict          = dict(loaded)
        as_dict['group'] = "basic"
        new_spec         = TaskSpec.build(as_dict)
        assert(isinstance(new_spec, TaskSpec))
        assert(str(new_spec.name) == str(task.spec.name))
