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

# ##-- 3rd party imports
import networkx as nx
import pytest

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot

import doot.errors
from doot.workflow._interface import TaskStatus_e
from doot.workflow import TaskSpec, TaskName, TaskArtifact
from doot.util import mock_gen

# ##-- end 1st party imports

from ..naive_tracker import NaiveTracker
from ..network import TrackNetwork
from ..queue import TrackQueue
from ..registry import TrackRegistry

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types
logging = logmod.root
logmod.getLogger("jgdv").propagate = False
logmod.getLogger("doot.control.tracker.registry").propagate = False
logmod.getLogger("doot.util").propagate = False

@pytest.fixture(scope="function")
def queue():
    tracker = NaiveTracker()
    return tracker._queue

##--|

class TestTrackerQueue:

    def test_sanity(self, queue):
        assert(isinstance(queue, TrackQueue))

    def test_tracker_bool(self, queue):
        obj = queue
        spec  = queue._tracker._factory.build({"name":"basic::task"})
        obj._tracker.register(spec)
        assert(not bool(obj._queue))
        assert(not bool(obj))
        instance = obj.queue_entry(spec.name)
        assert(bool(obj._queue))
        assert(bool(obj))

    def test_queue_task(self, queue):
        obj = queue
        spec  = queue._tracker._factory.build({"name":"basic::task"})
        obj._tracker.register(spec)
        assert(not bool(obj._queue))
        instance = obj.queue_entry(spec.name)
        assert(instance in obj.active_set)
        assert(bool(obj._queue))

    def test_queue_task_idempotnent(self, queue):
        obj = queue
        spec  = queue._tracker._factory.build({"name":"basic::task"})
        obj._tracker.register(spec)
        assert(not bool(obj._queue))
        instance = obj.queue_entry(spec.name)
        assert(instance in obj.active_set)
        assert(bool(obj._queue))
        assert(len(obj.active_set) == 1)
        instance = obj.queue_entry(spec.name)
        assert(len(obj.active_set) == 1)

    def test_queue_task_fail_when_not_registered(self, queue):
        obj = queue
        spec  = queue._tracker._factory.build({"name":"basic::task"})
        name1 = TaskName("basic::task")
        with pytest.raises(doot.errors.TrackingError):
            obj.queue_entry(name1)

    def test_queue_artifiact(self, queue):
        obj = queue
        artifact = TaskArtifact(pl.Path("test.txt"))
        # Stub artifact entry in tracker:
        obj._tracker.register(artifact)
        obj._tracker._connect(artifact)
        assert(not bool(obj))
        result = obj.queue_entry(artifact)
        assert(bool(obj))
        assert(artifact is result)

    def test_deque_task(self, queue):
        obj = queue
        spec  = queue._tracker._factory.build({"name":"basic::task"})
        spec2 = queue._tracker._factory.build({"name":"basic::other"})
        obj._tracker.register(spec, spec2)
        instance = obj.queue_entry(spec.name)
        instance2 = obj.queue_entry(spec2.name)
        assert(instance in obj.active_set)
        assert(instance2 in obj.active_set)
        val = obj.deque_entry()
        assert(val == instance)
        assert(instance in obj.active_set)

    def test_deque_artifact(self, queue):
        obj = queue
        artifact = TaskArtifact(pl.Path("test.txt"))
        # stub artifact in tracker:
        obj._tracker.register(artifact)
        obj._tracker._connect(artifact)
        result   = obj.queue_entry(artifact)
        assert(bool(obj))
        val = obj.deque_entry()
        assert(not bool(obj))
        assert(val is artifact)

    def test_peek_task(self, queue):
        obj = queue
        spec  = queue._tracker._factory.build({"name":"basic::task"})
        spec2 = queue._tracker._factory.build({"name":"basic::other"})
        obj._tracker.register(spec, spec2)
        instance  = obj.queue_entry(spec.name)
        instance2 = obj.queue_entry(spec2.name)
        assert(instance in obj.active_set)
        assert(instance2 in obj.active_set)
        val = obj.deque_entry(peek=True)
        assert(val == instance)
        assert(instance in obj.active_set)

    def test_clear_queue(self, queue):
        obj = queue
        spec  = queue._tracker._factory.build({"name":"basic::task"})
        obj._tracker.register(spec)
        instance = obj.queue_entry(spec.name)
        assert(bool(obj.active_set))
        obj.clear_queue()
        assert(not bool(obj.active_set))
