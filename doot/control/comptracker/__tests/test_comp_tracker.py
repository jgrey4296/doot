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
import pytest
import networkx as nx

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
doot._test_setup()
import doot.errors
import doot.structs
from doot._abstract import Task_i
from doot.control.comptracker.comp_tracker import ComponentTracker
from doot.enums import TaskStatus_e
from doot.utils import mock_gen

# ##-- end 1st party imports

logging = logmod.root

TaskSpec = doot.structs.TaskSpec
TaskName = doot.structs.TaskName

class TestCompTracker:

    def test_sanity(self):
        assert(True)
        assert(not False)

    def test_basic(self):
        obj = ComponentTracker()
        assert(isinstance(obj, ComponentTracker))

    def test_next_for_fails_with_unbuilt_network(self):
        obj = ComponentTracker()
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.next_for()

    def test_next_for_empty(self):
        obj = ComponentTracker()
        obj.build_network()
        assert(obj.next_for() is None)

    def test_next_for_no_connections(self):
        obj  = ComponentTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::Task"})
        obj.register_spec(spec)
        t_name = obj.queue_entry(spec.name)
        assert(obj.get_status(t_name) is TaskStatus_e.INIT)
        obj.build_network()
        match obj.next_for():
            case Task_i():
                assert(True)
            case _:
                assert(False)
        assert(obj.get_status(t_name) is TaskStatus_e.RUNNING)

    def test_next_simple_dependendency(self):
        obj  = ComponentTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name = obj.queue_entry(spec.name, from_user=True)
        assert(obj.get_status(t_name) is TaskStatus_e.INIT)
        obj.build_network()
        match obj.next_for():
            case Task_i() as result:
                assert(dep.name < result.name)
                assert(True)
            case _:
                assert(False)
        assert(obj.get_status(t_name) is TaskStatus_e.WAIT)

    def test_next_dependency_success_produces_ready_state_(self):
        obj  = ComponentTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name = obj.queue_entry(spec.name, from_user=True)
        assert(obj.get_status(t_name) is TaskStatus_e.INIT)
        obj.build_network()
        dep_inst = obj.next_for()
        assert(dep.name < dep_inst.name)
        obj.set_status(dep_inst.name, TaskStatus_e.SUCCESS)
        match obj.next_for():
            case Task_i() as result:
                assert(spec.name < result.name)
                assert(True)
            case _:
                assert(False)
        assert(obj.get_status(t_name) is TaskStatus_e.RUNNING)

    def test_next_artificial_success(self):
        obj  = ComponentTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name   = obj.queue_entry(spec.name)
        dep_inst = obj.queue_entry(dep.name)
        assert(obj.get_status(t_name) is TaskStatus_e.INIT)
        obj.build_network()
        # Force the dependency to success without getting it from next_for:
        obj.set_status(dep_inst, TaskStatus_e.SUCCESS)
        match obj.next_for():
            case Task_i() as result:
                assert(spec.name < result.name)
                assert(True)
            case _:
                assert(False)
        assert(obj.get_status(t_name) is TaskStatus_e.RUNNING)

    def test_next_halt(self):
        obj  = ComponentTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name   = obj.queue_entry(spec.name, from_user=True)
        dep_inst = obj.queue_entry(dep.name)
        assert(obj.get_status(t_name) is TaskStatus_e.INIT)
        obj.build_network()
        # Force the dependency to success without getting it from next_for:
        obj.set_status(dep_inst, TaskStatus_e.HALTED)
        match obj.next_for():
            case Task_i() as task:
                assert(task.name.is_cleanup())
            case x:
                assert(False), x

        for x in obj._registry.tasks.values():
            if x.name.is_cleanup():
                continue
            assert(x.status in [TaskStatus_e.HALTED, TaskStatus_e.DEAD])

    def test_next_fail(self):
        obj  = ComponentTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name   = obj.queue_entry(spec.name, from_user=True)
        dep_inst = obj.queue_entry(dep.name)
        assert(obj.get_status(t_name) is TaskStatus_e.INIT)
        obj.build_network()
        # Force the dependency to success without getting it from next_for:
        obj.set_status(dep_inst, TaskStatus_e.FAILED)
        match obj.next_for():
            case Task_i() as task:
                assert(task.name.is_cleanup())
            case x:
                assert(False), x

        for x in obj._registry.tasks.values():
            if x.name.is_cleanup():
                continue
            assert(x.status in [TaskStatus_e.DEAD])

    def test_next_job_head(self):
        obj       = ComponentTracker()
        job_spec  = doot.structs.TaskSpec.build({"name":"basic::job", "meta": ["JOB"], "cleanup":["basic::task"]})
        task_spec = doot.structs.TaskSpec.build({"name":"basic::task", "test_key": "bloo"})
        obj.register_spec(job_spec)
        obj.register_spec(task_spec)
        obj.queue_entry(job_spec, from_user=True)
        assert(job_spec.name in obj._registry.concrete)
        obj.build_network()
        assert(bool(obj._queue.active_set))
        assert(obj._network.is_valid)
        # head is in network
        match obj.next_for():
            case Task_i() as task:
                assert(job_spec.name < task.name)
                obj.set_status(task.name, TaskStatus_e.SUCCESS)
                assert(obj._network.is_valid)
            case x:
                assert(False), x

        match obj.next_for():
            case Task_i() as task:
                assert(job_spec.name.with_head() < task.name)
                assert(task.name.is_head())
                obj.set_status(task.name, TaskStatus_e.SUCCESS)
                assert(obj._network.is_valid)
                # A new job head hasn't been built
                assert(len(obj._registry.concrete[job_spec.name.with_head()]) == 1)
            case x:
                assert(False), x

        match obj.next_for():
            case Task_i():
                pass
            case x:
                assert(False), x

    def test_next_job_head_with_subtasks(self):
        obj       = ComponentTracker()
        job_spec  = doot.structs.TaskSpec.build({"name":"basic::job", "meta": ["JOB"]})
        sub_spec1 = doot.structs.TaskSpec.build({"name":"basic::task.1", "test_key": "bloo", "required_for": ["basic::job.$head$"]})
        sub_spec2 = doot.structs.TaskSpec.build({"name":"basic::task.2", "test_key": "blah", "required_for": ["basic::job.$head$"]})
        obj.register_spec(job_spec)
        obj.queue_entry(job_spec, from_user=True)
        assert(job_spec.name in obj._registry.concrete)
        # assert(job_spec.name.job_head() in obj._registry.concrete)
        conc_job_body = obj._registry.concrete[job_spec.name][-1]
        # conc_job_head = obj._registry.concrete[job_spec.name.job_head()][0]
        obj.build_network()
        # assert(conc_job_head in obj.network.nodes)
        assert(bool(obj._queue.active_set))
        job_body = obj.next_for()
        assert(job_body.name == conc_job_body)
        # Check head hasn't been added to network:
        # assert(conc_job_head in obj.network.nodes)
        # Add Tasks that the body generates:
        obj.queue_entry(sub_spec1)
        obj.queue_entry(sub_spec2)
        obj.build_network()
        # Artificially set priority of job body to force handling its success
        job_body.priority = 11
        obj._queue._queue.add(job_body.name, priority=job_body.priority)
        obj.set_status(conc_job_body, TaskStatus_e.SUCCESS)
        result = obj.next_for()
        # Next task is one of the new subtasks
        assert(any(x < result.name for x in [sub_spec1.name, sub_spec2.name]))