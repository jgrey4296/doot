#!/usr/bin/env python2
"""

"""
##-- imports
from __future__ import annotations

import logging as logmod
import unittest
import warnings
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
##-- end imports
logging = logmod.root

import pytest
import doot
doot._test_setup()

import doot.errors
from doot.enums import TaskStatus_e
import doot.structs
from doot.control.tracker import DootTracker
from doot._abstract import Task_i
from doot.utils import mock_gen

from doot.control.tracker import DootTracker

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

    def test_spec_retrieval(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = doot.structs.DootTaskName.build("basic::task")
        obj.register_spec(spec)
        retrieved = obj.specs[name]
        assert(retrieved == spec)

    def test_add_artifact(self):
        obj = DootTracker()
        artifact = doot.structs.DootTaskArtifact.build("simple/artifact.txt")
        assert(not bool(obj.artifacts))
        obj.add_artifact(artifact)
        assert(bool(obj.artifacts))

    @pytest.mark.xfail
    def test_artifact_retrival(self):
        obj = DootTracker()
        artifact = doot.structs.DootTaskArtifact.build("simple/artifact.txt")
        obj.add_artifact(artifact)
        matched = [x for x in obj.artifacts if x == "simple/artifact.txt"]
        assert(bool(matched))
        assert(matched[0] == artifact)

    def test_task_instantiation(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = doot.structs.DootTaskName.build("basic::task")
        obj.register_spec(spec)
        task = spec.make()
        assert(not bool(obj.tasks))
        obj.add_task(task)
        assert(bool(obj.tasks))

    def test_task_retrieval(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = doot.structs.DootTaskName.build("basic::task")
        obj.register_spec(spec)
        task = spec.make()
        obj.add_task(task)
        retrieved = obj.tasks[name]
        assert(retrieved == task)

    def test_task_status(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = doot.structs.DootTaskName.build("basic::task")
        obj.register_spec(spec)
        task = spec.make()
        obj.add_task(task)
        status = obj.task_status(name)
        assert(status is TaskStatus_e.WAIT)

    def test_task_status_fail_missing_task(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = doot.structs.DootTaskName.build("basic::task")
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.task_status(name)

    def test_update_status(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = doot.structs.DootTaskName.build("basic::task")
        obj.register_spec(spec)
        task = spec.make()
        obj.add_task(task)
        assert(obj.task_status(name) is TaskStatus_e.WAIT)
        obj.update_status(name, TaskStatus_e.SUCCESS)
        assert(obj.task_status(name) is TaskStatus_e.SUCCESS)

    def test_update_status_fail_missing_task(self):
        obj = DootTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = doot.structs.DootTaskName.build("basic::task")
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.update_status(name, TaskStatus_e.SUCCESS)

    def test_connect_task(self):
        obj = DootTracker()
        name1 = doot.structs.DootTaskName.build("basic::task")
        name2 = doot.structs.DootTaskName.build("basic::other")
        # Mock the tasks:
        obj.tasks[name1] = True
        obj.tasks[name2] = True

        assert(len(obj.network) == 1)
        obj.connect(name1, name2)
        assert(len(obj.network) == 3)
        assert(name1 in obj.network)
        assert(name2 in obj.network)

    def test_connect_artifact(self):
        obj = DootTracker()
        name1 = doot.structs.DootTaskName.build("basic::task")
        artifact = doot.structs.DootTaskArtifact.build("a/simple/artifact.txt")
        # Mock the task/artifact:
        obj.tasks[name1] = True
        obj.artifacts.add(artifact)

        assert(len(obj.network) == 1)
        obj.connect(name1, artifact)
        assert(len(obj.network) == 3)
        assert(name1 in obj.network)
        assert(artifact in obj.network)

    def test_connect_fail_no_artifact(self):
        obj = DootTracker()
        name1 = doot.structs.DootTaskName.build("basic::task")
        artifact = doot.structs.DootTaskArtifact.build("a/simple/artifact.txt")
        # Mock the task/artifact:
        obj.tasks[name1] = True
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.connect(name1, artifact)

    def test_connect_fail_no_tasks(self):
        obj = DootTracker()
        name1 = doot.structs.DootTaskName.build("basic::task")
        name2 = doot.structs.DootTaskName.build("basic::other")
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.connect(name1, name2)

    def test_network_retrieval(self):
        obj = DootTracker()
        name1 = doot.structs.DootTaskName.build("basic::task")
        name2 = doot.structs.DootTaskName.build("basic::other")
        # Mock the tasks:
        obj.tasks[name1] = True
        obj.tasks[name2] = True
        obj.connect(name1, name2)
        assert(name2 in obj.network.adj[name1])

    def test_task_queue(self, mocker):
        obj   = DootTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name1 = doot.structs.DootTaskName.build("basic::task")
        # Mock the task:
        obj.tasks[name1] = mocker.Mock(priority=5)
        assert(name1 not in obj.active_set)
        assert(not bool(obj._queue))
        obj.queue_task(name1)
        assert(name1 in obj.active_set)
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
        name1 = doot.structs.DootTaskName.build("basic::task")
        name2 = doot.structs.DootTaskName.build("basic::other")
        # Mock the task:
        obj.tasks[name1] = mocker.Mock(priority=5)
        obj.tasks[name2] = mocker.Mock(priority=2)
        obj.queue_task(name1)
        obj.queue_task(name2)
        val = obj.deque()
        assert(val == name1)
        assert(name1 not in obj.active_set)

    def test_clear_queue(self, mocker):
        obj   = DootTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name1 = doot.structs.DootTaskName.build("basic::task")
        name2 = doot.structs.DootTaskName.build("basic::other")
        # Mock the task:
        obj.tasks[name1] = mocker.Mock(priority=5)
        obj.tasks[name2] = mocker.Mock(priority=2)
        obj.queue_task(name1)
        obj.queue_task(name2)
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
