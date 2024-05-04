#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import unittest
import warnings
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

logging = logmod.root

# ##-- stdlib imports
from uuid import UUID

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
doot._test_setup()
import doot.errors
import doot.structs
from doot._abstract import Task_i
from doot.control.base_tracker import BaseTracker
from doot.control.tracker import DootTracker
from doot.enums import TaskStatus_e
from doot.utils import mock_gen

# ##-- end 1st party imports

class TestTrackerBasics:

    def test_basic(self):
        obj = DootTracker()
        assert(obj is not None)

    def test_register_spec(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        assert(not bool(obj.specs))
        obj.register_spec(spec)
        assert(bool(obj.specs))

    def test_register_spec_with_artifacts(self):
        obj = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task", "depends_on":["file:>test.txt"], "required_for": ["file:>other.txt"]})
        assert(not bool(obj.artifacts))
        obj.register_spec(spec)
        obj.register_artifacts(spec.name)
        assert(bool(obj.artifacts))

    def test_register_spec_pass_on_duplicate(self):
        obj = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        assert(len(obj.specs) == 1)
        obj.register_spec(spec)
        assert(len(obj.specs) == 1)

    def test_register_spec_ignores_disabled(self):
        obj = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task", "disabled":True})
        assert(len(obj.specs) == 0)
        obj.register_spec(spec)
        assert(len(obj.specs) == 0)

    def test_spec_retrieval(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        retrieved = obj.specs[name]
        assert(retrieved == spec)

    def test_task_instantiation(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        assert(not bool(obj.tasks))
        obj._make_task(instance)
        assert(bool(obj.tasks))

    def test_task_retrieval(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        result = obj._make_task(instance)
        retrieved        = obj.tasks[result]
        assert(isinstance(retrieved, Task_i))

    def test_task_status(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        result   = obj._make_task(instance)
        status   = obj.task_status(result)
        assert(status is TaskStatus_e.WAIT)

    def test_task_status_fail_missing_task(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = spec.name
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.task_status(name)

    def test_update_status(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        result = obj._make_task(instance)
        assert(obj.task_status(result) is TaskStatus_e.WAIT)
        obj.update_status(result, TaskStatus_e.SUCCESS)
        assert(obj.task_status(result) is TaskStatus_e.SUCCESS)

    def test_update_status_fail_missing_task(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = spec.name
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.update_status(name, TaskStatus_e.SUCCESS)

class TestTrackerNetwork:

    def test_network_connect_to_root(self):
        obj = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        assert(bool(obj.network.pred[obj._root_node]))
        assert(bool(obj.network.succ[instance]))

    def test_connect_task(self):
        obj = DootTracker()
        name1 = doot.structs.DootTaskName.build("basic::task").instantiate()
        name2 = doot.structs.DootTaskName.build("basic::other").instantiate()
        # Mock the specs:
        obj.specs[name1] = True
        obj.specs[name2] = True

        assert(len(obj.network) == 1)
        obj.connect(name1, name2)
        assert(len(obj.network) == 3)
        assert(name1 in obj.network)
        assert(name2 in obj.network)
        assert(name2 in obj.network.succ[name1])
        assert(name1 in obj.network.pred[name2])

    def test_connect_artifact(self):
        obj = DootTracker()
        name1 = doot.structs.DootTaskName.build("basic::task").instantiate()
        artifact = doot.structs.DootTaskArtifact.build("a/simple/artifact.txt")
        # Mock the task/artifact:
        obj.specs[name1] = True
        obj.artifacts[artifact] = []

        assert(len(obj.network) == 1)
        obj.connect(name1, artifact)
        assert(len(obj.network) == 3)
        assert(name1 in obj.network)
        assert(artifact in obj.network)
        assert(artifact in obj.network.succ[name1])
        assert(name1 in obj.network.pred[artifact])

    def test_connect_fail_no_artifact(self):
        obj = DootTracker()
        name1 = doot.structs.DootTaskName.build("basic::task").instantiate()
        artifact = doot.structs.DootTaskArtifact.build("a/simple/artifact.txt")
        # Mock the task/artifact:
        obj.specs[name1] = True
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.connect(name1, artifact)

    def test_connect_fail_no_tasks(self):
        obj = DootTracker()
        name1 = doot.structs.DootTaskName.build("basic::task").instantiate()
        name2 = doot.structs.DootTaskName.build("basic::other").instantiate()
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.connect(name1, name2)

    def test_network_retrieval(self):
        obj = DootTracker()
        name1 = doot.structs.DootTaskName.build("basic::task").instantiate()
        name2 = doot.structs.DootTaskName.build("basic::other").instantiate()
        # Mock the tasks:
        obj.specs[name1] = True
        obj.specs[name2] = True
        obj.connect(name1, name2)
        assert(name2 in obj.network.adj[name1])

    def test_task_queue(self, mocker):
        obj   = DootTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task", "priority":5})
        name1 = doot.structs.DootTaskName.build("basic::task")
        obj.register_spec(spec)
        instance = obj._instantiate_spec(spec.name)
        # Mock the task:
        obj.tasks[instance] = mocker.Mock(priority=5)
        assert(instance not in obj.active_set)
        assert(not bool(obj._queue))
        obj.queue_task(instance)
        assert(instance in obj.active_set)
        assert(bool(obj._queue))

    def test_task_queue_fail_with_no_tasks(self):
        obj   = DootTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name1 = doot.structs.DootTaskName.build("basic::task")
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.queue_task(name1)

    def test_deque_task(self, mocker):
        obj   = DootTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        spec2  = doot.structs.DootTaskSpec.build({"name":"basic::other"})
        obj.register_spec(spec)
        obj.register_spec(spec2)
        instance  = obj._instantiate_spec(spec.name)
        instance2 = obj._instantiate_spec(spec2.name)
        # Mock the task:
        obj.tasks[instance] = mocker.Mock(priority=5)
        obj.tasks[instance2] = mocker.Mock(priority=2)
        obj.queue_task(instance)
        obj.queue_task(instance2)
        assert(instance in obj.active_set)
        assert(instance2 in obj.active_set)
        val = obj.deque()
        assert(val == instance)
        assert(instance not in obj.active_set)

    def test_clear_queue(self, mocker):
        obj    = DootTracker()
        spec   = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        instance = obj._instantiate_spec(spec.name)
        # Mock the task:
        obj.tasks[instance] = mocker.Mock(priority=5)
        obj.queue_task(instance)
        assert(bool(obj.active_set))
        obj.clear_queue()
        assert(not bool(obj.active_set))

class TestTrackerExtensions:

    def test_basic(self):
        obj = DootTracker()
        assert(obj is not None)

class TestTrackerUsage:
    """ The basic pattern of tracker usage:
    1) register task specs
    2) instantiate specs as a tasks
    3) queue them
    4) build the dependency network (expands and instantites the dependencies)
    6) call next_for to get the next task
    8) perform the task
    9) update its status
    10) return to (5) until no more tasks

    """

    def test_basic(self):
        obj = DootTracker()
