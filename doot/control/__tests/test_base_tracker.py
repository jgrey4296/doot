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


class TestTrackerStore:

    def test_basic(self):
        obj = BaseTracker()
        assert(obj is not None)

    def test_register_spec(self):
        obj = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        assert(not bool(obj.specs))
        obj.register_spec(spec)
        assert(bool(obj.specs))

    def test_register_spec_pass_on_duplicate(self):
        obj = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        assert(len(obj.specs) == 1)
        obj.register_spec(spec)
        assert(len(obj.specs) == 1)

    def test_spec_retrieval(self):
        obj = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        retrieved = obj.specs[name]
        assert(retrieved == spec)

    def test_add_artifact(self):
        obj = BaseTracker()
        artifact = doot.structs.DootTaskArtifact.build("simple/artifact.txt")
        assert(not bool(obj.artifacts))
        obj.add_artifact(artifact)
        assert(bool(obj.artifacts))

    @pytest.mark.xfail
    def test_artifact_retrival(self):
        obj = BaseTracker()
        artifact = doot.structs.DootTaskArtifact.build("simple/artifact.txt")
        obj.add_artifact(artifact)
        matched = [x for x in obj.artifacts if x == "simple/artifact.txt"]
        assert(bool(matched))
        assert(matched[0] == artifact)

    def test_task_instantiation(self):
        obj = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        assert(not bool(obj.tasks))
        obj._make_task(instance)
        assert(bool(obj.tasks))

    def test_task_retrieval(self):
        obj = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        result = obj._make_task(instance)
        retrieved = obj.tasks[result]
        assert(isinstance(retrieved, Task_i))

    def test_task_status(self):
        obj = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        result   = obj._make_task(instance)
        status   = obj.task_status(result)
        assert(status is TaskStatus_e.WAIT)

    def test_task_status_fail_missing_task(self):
        obj = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = spec.name
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.task_status(name)

    def test_update_status(self):
        obj = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        result = obj._make_task(instance)
        assert(obj.task_status(result) is TaskStatus_e.WAIT)
        obj.update_status(result, TaskStatus_e.SUCCESS)
        assert(obj.task_status(result) is TaskStatus_e.SUCCESS)

    def test_update_status_fail_missing_task(self):
        obj = BaseTracker()
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

    def test_connect_task(self):
        obj = BaseTracker()
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

    def test_connect_artifact(self):
        obj      = BaseTracker()
        name1    = doot.structs.DootTaskName.build("basic::task").instantiate()
        artifact = doot.structs.DootTaskArtifact.build("a/simple/artifact.txt")
        # Mock the task/artifact:
        obj.specs[name1] = True
        obj.artifacts.add(artifact)

        assert(len(obj.network) == 1)
        obj.connect(name1, artifact)
        assert(len(obj.network) == 3)
        assert(name1 in obj.network)
        assert(artifact in obj.network)

    def test_connect_fail_no_artifact(self):
        obj      = BaseTracker()
        name1    = doot.structs.DootTaskName.build("basic::task").instantiate()
        artifact = doot.structs.DootTaskArtifact.build("a/simple/artifact.txt")
        # Mock the task/artifact:
        obj.specs[name1] = True
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.connect(name1, artifact)

    def test_connect_fail_no_tasks(self):
        obj = BaseTracker()
        name1 = doot.structs.DootTaskName.build("basic::task").instantiate()
        name2 = doot.structs.DootTaskName.build("basic::other").instantiate()
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.connect(name1, name2)

    def test_network_retrieval(self):
        obj = BaseTracker()
        name1 = doot.structs.DootTaskName.build("basic::task").instantiate()
        name2 = doot.structs.DootTaskName.build("basic::other").instantiate()
        # Mock the tasks:
        obj.specs[name1] = True
        obj.specs[name2] = True
        obj.connect(name1, name2)
        assert(name2 in obj.network.adj[name1])

    def test_network_build_empty(self):
        obj = BaseTracker()
        assert(len(obj.network) == 1)
        assert(not bool(obj.tasks))
        assert(not bool(obj.specs))
        obj.build_network()
        assert(len(obj.network) == 1)

    def test_network_build_single_dependency_node(self):
        obj  = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task", "depends_on":["basic::dep"]})
        spec2 = doot.structs.DootTaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec)
        obj.register_spec(spec2)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        instance = obj._instantiate_spec(spec.name)
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(len(obj.network) == 3)
        assert(obj.concrete[spec2.name][0] in obj.network.pred[instance])

    def test_network_build_single_dependent_node(self):
        obj   = BaseTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task", "required_for":["basic::req"]})
        spec2 = doot.structs.DootTaskSpec.build({"name":"basic::req"})
        obj.register_spec(spec)
        obj.register_spec(spec2)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(len(obj.network) == 3)
        assert(obj.concrete[spec2.name][0] in obj.network.succ[instance])

    def test_network_build_dep_chain(self):
        obj  = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task", "depends_on":["basic::dep"]})
        spec2 = doot.structs.DootTaskSpec.build({"name":"basic::dep", "depends_on":["basic::chained"]})
        spec3 = doot.structs.DootTaskSpec.build({"name":"basic::chained"})
        obj.register_spec(spec)
        obj.register_spec(spec2)
        obj.register_spec(spec3)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(len(obj.network) == 4)
        assert(obj.concrete[spec2.name][0] in obj.network.pred[instance])
        assert(obj.concrete[spec3.name][0] in obj.network.pred[obj.concrete[spec2.name][0]])

    def test_network_build_dep_match_no_keys(self):
        obj   = BaseTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "keys":[]}], "test_key": "bloo"})
        spec2 = doot.structs.DootTaskSpec.build({"name":"basic::dep", "test_key": "blah"})
        obj.register_spec(spec)
        obj.register_spec(spec2)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(len(obj.network) == 3)
        assert(obj.concrete[spec2.name][0] in obj.network.pred[instance])

    def test_network_build_dep_match_with_key(self):
        obj   = BaseTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "keys":["test_key"]}], "test_key": "bloo"})
        spec2 = doot.structs.DootTaskSpec.build({"name":"basic::dep", "test_key": "blah"})
        obj.register_spec(spec)
        obj.register_spec(spec2)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(len(obj.network) == 3)
        pred = list(obj.network.pred[instance])[0]
        assert(spec2.name  < pred)
        assert(spec.test_key == obj.specs[pred].test_key)

    def test_build_network_dep_chain(self):
        obj   = BaseTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "keys":["test_key"]}], "test_key": "bloo"})
        spec2 = doot.structs.DootTaskSpec.build({"name":"basic::dep", "depends_on": [{"task":"basic::chained", "keys":["test_key"]}], "test_key": "blah"})
        spec3 = doot.structs.DootTaskSpec.build({"name":"basic::chained", "test_key": "aweg"})
        obj.register_spec(spec)
        obj.register_spec(spec2)
        obj.register_spec(spec3)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(len(obj.network) == 4)
        pred1 = list(obj.network.pred[instance])[0]
        assert(spec2.name  < pred1)
        assert(spec.test_key == obj.specs[pred1].test_key)
        assert(obj.specs[pred1].source == spec2.name)
        assert(obj.specs[pred1].test_key != spec2.test_key)

        pred2 = list(obj.network.pred[pred1])[0]
        assert(spec3.name  < pred2)
        assert(spec.test_key == obj.specs[pred2].test_key)
        assert(obj.specs[pred2].source == spec3.name)
        assert(obj.specs[pred2].test_key != spec3.test_key)

    def test_build_network_req_chain(self):
        obj   = BaseTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task", "required_for":[{"task":"basic::dep", "keys":["test_key"]}], "test_key": "bloo"})
        spec2 = doot.structs.DootTaskSpec.build({"name":"basic::dep", "required_for": [{"task":"basic::chained", "keys":["test_key"]}], "test_key": "blah"})
        spec3 = doot.structs.DootTaskSpec.build({"name":"basic::chained", "test_key": "aweg"})
        obj.register_spec(spec)
        obj.register_spec(spec2)
        obj.register_spec(spec3)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(len(obj.network) == 4)
        succ1 = list(obj.network.succ[instance])[1] # note: index 1 this time, to skip root
        assert(spec2.name  < succ1)
        assert(spec.test_key == obj.specs[succ1].test_key)
        assert(obj.specs[succ1].source == spec2.name)
        assert(obj.specs[succ1].test_key != spec2.test_key)

        succ2 = list(obj.network.succ[succ1])[0]
        assert(spec3.name  < succ2)
        assert(spec.test_key == obj.specs[succ2].test_key)
        assert(obj.specs[succ2].source == spec3.name)
        assert(obj.specs[succ2].test_key != spec3.test_key)


    def test_build_network_with_head_dep(self):
        obj   = BaseTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task", "depends_on":["basic::dep.$head$"], "test_key": "bloo"})
        spec2 = doot.structs.DootTaskSpec.build({"name":"basic::dep", "flags": ["JOB"]})
        obj.register_spec(spec)
        obj.register_spec(spec2)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(spec.name in obj.concrete)
        assert(spec2.name.job_head() in obj.concrete)
        assert(spec2.name in obj.concrete)
        obj.validate_network()



class TestTrackerQueue:

    def test_task_queue(self, mocker):
        obj   = BaseTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        instance = obj._instantiate_spec(spec.name)
        # Mock the task:
        obj.tasks[instance] = mocker.Mock(priority=5)
        assert(instance not in obj.active_set)
        assert(not bool(obj._queue))
        obj.queue_task(instance)
        assert(instance in obj.active_set)
        assert(bool(obj._queue))

    def test_task_queue_fail_when_not_registered(self):
        obj   = BaseTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        name1 = doot.structs.DootTaskName.build("basic::task")
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.queue_task(name1)

    def test_deque_task(self, mocker):
        obj   = BaseTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        spec2 = doot.structs.DootTaskSpec.build({"name":"basic::other"})
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
        obj   = BaseTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        instance = obj._instantiate_spec(spec.name)
        # Mock the task:
        obj.tasks[instance] = mocker.Mock(priority=5)
        obj.queue_task(instance)
        assert(bool(obj.active_set))
        obj.clear_queue()
        assert(not bool(obj.active_set))

class TestTrackerInternals:

    def test_basic(self):
        obj = BaseTracker()
        assert(obj is not None)

    def test_instantiate_spec_no_op(self):
        obj       = BaseTracker()
        base_spec = doot.structs.DootTaskSpec.build({"name":"basic::task"})
        spec      = doot.structs.DootTaskSpec.build({"name":"test::spec"})
        obj.register_spec(base_spec)
        obj.register_spec(spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec is not special)
        assert(spec is not base_spec)
        assert(spec.name < special)
        assert(special in obj.concrete[spec.name])

    def test_instantiate_spec(self):
        obj = BaseTracker()
        base_spec = doot.structs.DootTaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        dep_spec = doot.structs.DootTaskSpec.build({"name": "example::dep"})
        spec    = doot.structs.DootTaskSpec.build({"name":"test::spec", "source": "basic::task", "bloo": 15})
        obj.register_spec(base_spec)
        obj.register_spec(dep_spec)
        obj.register_spec(spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.DootTaskName))
        assert(special in obj.concrete[spec.name])


    def test_instantiate_head_spec(self):
        obj = BaseTracker()
        spec = doot.structs.DootTaskSpec.build({"name":"basic::task", "ctor": "doot.task.base_job:DootJob", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        abs_head = spec.name.job_head()
        obj.register_spec(spec)
        instance = obj._instantiate_spec(spec.name)
        inst_head = instance.job_head()
        assert(instance in obj.specs)
        assert(abs_head in obj.specs)
        assert(instance in obj.concrete[spec.name])
        assert(spec.name < abs_head)
        assert(spec.name < instance)
        assert(instance < inst_head)
        assert(inst_head not in obj.specs)


    def test_instantiate_spec_chain(self):
        obj = BaseTracker()
        base_spec = doot.structs.DootTaskSpec.build({"name":"basic::task", "blah": 2, "bloo": 5})
        dep_spec = doot.structs.DootTaskSpec.build({"name": "example::dep", "source":"basic::task", "bloo":10, "aweg":15 })
        spec    = doot.structs.DootTaskSpec.build({"name":"test::spec", "source": "example::dep", "aweg": 20})
        obj.register_spec(base_spec)
        obj.register_spec(dep_spec)
        obj.register_spec(spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.DootTaskName))

    def test_instantiate_spec_name_change(self):
        obj       = BaseTracker()
        base_spec = doot.structs.DootTaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        obj.register_spec(base_spec)
        dep_spec = doot.structs.DootTaskSpec.build({"name": "example::dep"})
        obj.register_spec(dep_spec)
        spec    = doot.structs.DootTaskSpec.build({"name":"test::spec", "source": "basic::task", "bloo": 15})
        obj.register_spec(spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.DootTaskName))
        assert(spec.name < special)
        assert(isinstance(special.tail[-1], UUID))

    def test_instantiate_spec_extra_merge(self):
        obj = BaseTracker()
        base_spec = doot.structs.DootTaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        obj.register_spec(base_spec)
        dep_spec = doot.structs.DootTaskSpec.build({"name": "example::dep"})
        obj.register_spec(dep_spec)
        spec    = doot.structs.DootTaskSpec.build({"name":"test::spec", "source": "basic::task", "bloo": 15, "aweg": "aweg"})
        obj.register_spec(spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.DootTaskName))
        concrete = obj.specs[special]
        assert(concrete.extra.blah == 2)
        assert(concrete.extra.bloo == 15)

    def test_instantiate_spec_depends_merge(self):
        obj = BaseTracker()
        base_spec = doot.structs.DootTaskSpec.build({"name":"basic::task", "depends_on":["example::dep"]})
        obj.register_spec(base_spec)
        dep_spec = doot.structs.DootTaskSpec.build({"name": "example::dep"})
        obj.register_spec(dep_spec)
        dep_spec2 = doot.structs.DootTaskSpec.build({"name": "another::dep"})
        obj.register_spec(dep_spec2)
        spec    = doot.structs.DootTaskSpec.build({"name":"test::spec", "source": "basic::task", "depends_on":["another::dep"]})
        obj.register_spec(spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.DootTaskName))
        concrete = obj.specs[special]
        assert(len(concrete.depends_on) == 2)
        assert("example::dep" in concrete.depends_on)
        assert("another::dep" in concrete.depends_on)


    def test_concrete_edges(self):
        obj   = BaseTracker()
        spec  = doot.structs.DootTaskSpec.build({"name":"basic::task",
            "depends_on":[{"task":"basic::dep", "keys":["test_key"]}],
            "required_for": ["basic::chained"],
            "test_key": "bloo"})
        spec2 = doot.structs.DootTaskSpec.build({"name":"basic::dep", "depends_on": [{"task":"basic::chained", "keys":["test_key"]}], "test_key": "blah"})
        spec3 = doot.structs.DootTaskSpec.build({"name":"basic::chained", "test_key": "aweg"})
        obj.register_spec(spec)
        obj.register_spec(spec2)
        obj.register_spec(spec3)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        result = obj.concrete_edges(instance)
        assert(isinstance(result, TomlGuard))
        assert(bool(result.pred.tasks))
        assert(spec2.name < result.pred.tasks[0])
        assert(bool(result.succ.tasks))
        assert(spec3.name < result.succ.tasks[0])
        assert(result.root is True)
