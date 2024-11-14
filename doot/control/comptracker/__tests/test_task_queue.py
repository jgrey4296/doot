#!/usr/bin/env python3
"""

"""
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

# ##-- 3rd party imports
import pytest
from tomlguard import TomlGuard
import networkx as nx

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
doot._test_setup()
import doot.errors
import doot.structs
from doot._abstract import Task_i
from doot.control.comptracker.task_registry import TaskRegistry
from doot.control.comptracker.task_network import TaskNetwork
from doot.control.comptracker.task_queue import TaskQueue
from doot.enums import TaskStatus_e
from doot.utils import mock_gen

# ##-- end 1st party imports

logging = logmod.root

@pytest.fixture(scope="function")
def queue():
    registry = TaskRegistry()
    network  = TaskNetwork(registry)
    return TaskQueue(registry, network)

class TestTrackerQueue:

    def test_sanity(self, queue):
        assert(isinstance(queue, TaskQueue))

    def test_tracker_bool(self, queue):
        obj = queue
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        obj._registry.register_spec(spec)
        assert(not bool(obj._queue))
        assert(not bool(obj))
        instance = obj.queue_entry(spec.name)
        assert(bool(obj._queue))
        assert(bool(obj))

    def test_queue_task(self, queue):
        obj = queue
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        obj._registry.register_spec(spec)
        assert(not bool(obj._queue))
        instance = obj.queue_entry(spec.name)
        assert(instance in obj.active_set)
        assert(bool(obj._queue))

    def test_queue_task_idempotnent(self, queue):
        obj = queue
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        obj._registry.register_spec(spec)
        assert(not bool(obj._queue))
        instance = obj.queue_entry(spec.name)
        assert(instance in obj.active_set)
        assert(bool(obj._queue))
        assert(len(obj.active_set) == 1)
        instance = obj.queue_entry(spec.name)
        assert(len(obj.active_set) == 1)

    def test_queue_task_fail_when_not_registered(self, queue):
        obj = queue
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        name1 = doot.structs.TaskName.build("basic::task")
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.queue_entry(name1)

    def test_queue_artifiact(self, queue):
        obj = queue
        artifact = doot.structs.TaskArtifact.build(pl.Path("test.txt"))
        # Stub artifact entry in tracker:
        obj._registry._register_artifact(artifact)
        obj._network._add_node(artifact)
        assert(not bool(obj))
        result = obj.queue_entry(artifact)
        assert(bool(obj))
        assert(artifact is result)

    def test_deque_task(self, queue):
        obj = queue
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::other"})
        obj._registry.register_spec(spec, spec2)
        instance = obj.queue_entry(spec.name)
        instance2 = obj.queue_entry(spec2.name)
        assert(instance in obj.active_set)
        assert(instance2 in obj.active_set)
        val = obj.deque_entry()
        assert(val == instance)
        assert(instance in obj.active_set)

    def test_deque_artifact(self, queue):
        obj = queue
        artifact = doot.structs.TaskArtifact.build(pl.Path("test.txt"))
        # stub artifact in tracker:
        obj._registry._register_artifact(artifact)
        obj._network._add_node(artifact)
        result   = obj.queue_entry(artifact)
        assert(bool(obj))
        val = obj.deque_entry()
        assert(not bool(obj))
        assert(val is artifact)

    def test_peek_task(self, queue):
        obj = queue
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::other"})
        obj._registry.register_spec(spec, spec2)
        instance  = obj.queue_entry(spec.name)
        instance2 = obj.queue_entry(spec2.name)
        assert(instance in obj.active_set)
        assert(instance2 in obj.active_set)
        val = obj.deque_entry(peek=True)
        assert(val == instance)
        assert(instance in obj.active_set)

    def test_clear_queue(self, queue):
        obj = queue
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        obj._registry.register_spec(spec)
        instance = obj.queue_entry(spec.name)
        assert(bool(obj.active_set))
        obj.clear_queue()
        assert(not bool(obj.active_set))
