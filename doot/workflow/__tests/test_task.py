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
from doot.cmds.structs.stub import TaskStub
from doot.workflow.factory import TaskFactory
from .. import TaskSpec, DootTask
from .. import _interface as API

basic_action  = lambda x: ftz.partial(lambda val, state: doot.report.gen.user("Got: %s : %s", val, state), x)
factory       = TaskFactory()

class TestBaseTask:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_ctor(self):
        assert(isinstance(DootTask, API.Task_p))
        match DootTask:
            case API.Task_p():
                assert(True)
            case x:
                assert(False), x

    def test_initial(self):
        spec = TaskSpec(name="basic::example")
        match DootTask(spec, job=None):
            case API.Task_p():
                assert(True)
            case x:
                 assert(False), x

    def test_lambda_action(self):
        spec = factory.build({"name":"basic::example", "action_ctor":basic_action})
        match DootTask(spec, job=None):
            case API.Task_p():
                assert(True)
            case x:
                 assert(False), x

    def test_expand_lambda_action(self):
        spec = factory.build({"name":"basic::example",
                               "action_ctor":basic_action,
                               "actions": [{"do": "doot.workflow.actions:DootBaseAction", "args":["blah"]}]})
        match DootTask(spec, job=None):
            case API.Task_p() as task:
                actions = list(task.get_action_group("actions"))
                assert(len(actions) == 1)
            case x:
                 assert(False), x

    def test_run_lambda_action(self, caplog):
        caplog.clear()
        caplog.set_level(logmod.NOTSET, logger=doot.report.log.name)
        spec = factory.build({"name":"basic::example", "action_ctor":basic_action, "actions": [{"do": "doot.workflow.actions:DootBaseAction", "args":["blah"]}]})
        match DootTask(spec, job=None):
            case API.Task_p() as task:
                task.prepare_actions()
                actions = list(task.get_action_group("actions"))
                result = actions[0]({"example": "state"})
                assert(result == {"count": 1})
                assert("Base Action Called: 0" in caplog.messages)
            case x:
                 assert(False), x

    def test_expand_action_str(self, caplog):
        caplog.set_level("DEBUG", logger=logging.root.name)
        spec = factory.build({"name":"basic::example", "action_ctor": "test_base_task:basic_action", "actions": [{"do": "doot.workflow.actions:DootBaseAction", "args":["blah"]}]})
        match DootTask(spec, job=None):
            case API.Task_p() as task:
                task.prepare_actions()
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
        task     = DootTask(factory.build({"name" : "basic::example", "flags" : ["TASK", "IDEMPOTENT"]}), job=None)
        stub     = task.stub_instance(stub_obj)
        assert(str(stub['name'].default) == "basic::example")
        as_str = stub.to_toml()

    @pytest.mark.xfail
    def test_toml_instance_stub_rebuild(self):
        """ take a stub and turn it into a task spec  """
        stub_obj         = TaskStub(ctor=DootTask)
        task             = DootTask(factory.build({"name" : "basic::example",
                                                    "flags" : ["TASK", "IDEMPOTENT"]}), job=None)
        stub             = task.stub_instance(stub_obj)
        as_str           = stub.to_toml()
        loaded           = ChainGuard.read(as_str)
        as_dict          = dict(loaded)
        new_spec         = factory.build(as_dict)
        assert(isinstance(new_spec, TaskSpec))
        assert(str(new_spec.name) == str(task.spec.name))
