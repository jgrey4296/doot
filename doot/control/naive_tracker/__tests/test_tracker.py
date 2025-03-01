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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot

# ##-- end 1st party imports


# ##-- 1st party imports
import doot.errors
import doot.structs
from doot.control.naive_tracker._core import BaseTracker
from doot.control.naive_tracker.tracker import NaiveTracker
from doot.enums import ExecutionPolicy_e, TaskStatus_e

# ##-- end 1st party imports

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
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|
from doot._abstract import Task_p
# isort: on
# ##-- end types

logging = logmod.root

class TestTrackerNext:

    def test_basic(self):
        obj = NaiveTracker()
        assert(isinstance(obj, NaiveTracker))


    def test_next_for_fails_with_unbuilt_network(self):
        obj = NaiveTracker()
        with pytest.raises(doot.errors.TrackingError):
            obj.next_for()


    def test_next_for_empty(self):
        obj = NaiveTracker()
        obj.build_network()
        assert(obj.next_for() is None)


    def test_next_for_no_connections(self):
        obj  = NaiveTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::Task"})
        obj.register_spec(spec)
        t_name = obj.queue_entry(spec.name)
        assert(obj.get_status(t_name) is TaskStatus_e.INIT)
        obj.build_network()
        match obj.next_for():
            case Task_p():
                assert(True)
            case _:
                assert(False)
        assert(obj.get_status(t_name) is TaskStatus_e.RUNNING)


    def test_next_simple_dependendency(self):
        # need to check on doot.args... results for this
        obj  = NaiveTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name = obj.queue_entry(spec.name, from_user=True)
        assert(obj.get_status(t_name) is TaskStatus_e.INIT)
        obj.build_network()
        match obj.next_for():
            case Task_p() as result:
                assert(dep.name < result.name)
                assert(True)
            case _:
                assert(False)
        assert(obj.get_status(t_name) is TaskStatus_e.WAIT)


    def test_next_dependency_success_produces_ready_state_(self):
        obj  = NaiveTracker()
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
            case Task_p() as result:
                assert(spec.name < result.name)
                assert(True)
            case _:
                assert(False)
        assert(obj.get_status(t_name) is TaskStatus_e.RUNNING)


    def test_next_artificial_success(self):
        obj  = NaiveTracker()
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
            case Task_p() as result:
                assert(spec.name < result.name)
                assert(True)
            case _:
                assert(False)
        assert(obj.get_status(t_name) is TaskStatus_e.RUNNING)


    def test_next_halt(self):
        obj  = NaiveTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name   = obj.queue_entry(spec.name, from_user=True)
        dep_inst = obj.queue_entry(dep.name)
        assert(obj.get_status(t_name) is TaskStatus_e.INIT)
        obj.build_network()
        # Force the dependency to success without getting it from next_for:
        obj.set_status(dep_inst, TaskStatus_e.HALTED)
        cleanup = obj.next_for()
        assert(isinstance(cleanup, Task_p))
        assert("$cleanup$" in cleanup.name)
        for x in obj.tasks.values():
            if "$cleanup$" in x.name:
                continue
            assert(x.status in [TaskStatus_e.HALTED, TaskStatus_e.DEAD])


    def test_next_fail(self):
        obj  = NaiveTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name   = obj.queue_entry(spec.name, from_user=True)
        dep_inst = obj.queue_entry(dep.name)
        assert(obj.get_status(t_name) is TaskStatus_e.INIT)
        obj.build_network()
        # Force the dependency to success without getting it from next_for:
        obj.set_status(dep_inst, TaskStatus_e.FAILED)
        cleanup = obj.next_for()
        assert("$cleanup$" in cleanup.name)
        for x in obj.tasks.values():
            if "$cleanup$" in x.name:
                continue
            assert(x.status in [TaskStatus_e.DEAD])

    def test_next_job_head(self):
        obj       = NaiveTracker()
        job_spec  = doot.structs.TaskSpec.build({"name":"basic::+.job", "meta": ["JOB"], "cleanup":["basic::task"]})
        task_spec = doot.structs.TaskSpec.build({"name":"basic::task", "test_key": "bloo"})
        obj.register_spec(job_spec)
        obj.register_spec(task_spec)
        obj.queue_entry(job_spec, from_user=True)
        assert(job_spec.name in obj.concrete)
        obj.build_network()
        assert(bool(obj.active_set))
        assert(obj.network_is_valid)
        match obj.next_for():
            case Task_p() as task if job_spec.name < task.name:
                obj.set_status(task, TaskStatus_e.SUCCESS)
                assert(obj.network_is_valid)
            case x:
                assert(False), x.name

        match obj.next_for():
            case Task_p() as task if job_spec.name.with_head() < task.name:
                obj.set_status(task.name, TaskStatus_e.SUCCESS)
                assert(obj.network_is_valid)
            case x:
                assert(False), x.name

        match obj.next_for():
            case Task_p() as task if task_spec.name < task.name:
                obj.set_status(task.name, TaskStatus_e.SUCCESS)
                assert(obj.network_is_valid)
            case x:
                assert(False), x.name

        match obj.next_for():
            case Task_p() as task if job_spec.name.with_head().with_cleanup() < task.name:
                obj.set_status(task.name, TaskStatus_e.SUCCESS)
                assert(obj.network_is_valid)
            case x:
                assert(False), x.name


    def test_next_job_head_with_subtasks(self):
        obj       = NaiveTracker()
        job_spec  = doot.structs.TaskSpec.build({"name":"basic::job", "flags": ["JOB"]})
        sub_spec1 = doot.structs.TaskSpec.build({"name":"basic::task.1", "test_key": "bloo", "required_for": ["basic::job.$head$"]})
        sub_spec2 = doot.structs.TaskSpec.build({"name":"basic::task.2", "test_key": "blah", "required_for": ["basic::job.$head$"]})
        obj.register_spec(job_spec)
        obj.queue_entry(job_spec, from_user=True)
        assert(job_spec.name in obj.concrete)
        # assert(job_spec.name.with_head() in obj.concrete)
        conc_job_body = obj.concrete[job_spec.name][-1]
        # conc_job_head = obj.concrete[job_spec.name.with_head()][0]
        obj.build_network()
        # assert(conc_job_head in obj.network.nodes)
        assert(bool(obj.active_set))
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
        obj._queue.add(job_body.name, priority=job_body.priority)
        obj.set_status(conc_job_body, TaskStatus_e.SUCCESS)
        result = obj.next_for()
        # Next task is one of the new subtasks
        assert(any(x < result.name for x in [sub_spec1.name, sub_spec2.name]))



class TestTrackerWalk:

    @pytest.fixture(scope="function")
    def specs(self):
        head = []
        tail = []

        head += [
            {"name":"basic::alpha", "depends_on":["basic::dep.1", "basic::dep.2"]},
            {"name":"basic::beta", "depends_on":["basic::dep.3"]},
            {"name":"basic::solo", "depends_on":[]},
        ]
        tail += [
            {"name":"basic::dep.1"},
            # {"name":"basic::dep.2"},
            {"name":"basic::dep.2", "depends_on" : ["basic::dep.4"]},
            {"name":"basic::dep.3"},
            # {"name":"basic::dep.4", "required_for":["basic::dep.2"]},
            {"name":"basic::dep.4", "required_for":[]},
        ]
        return ([doot.structs.TaskSpec.build(x) for x in head],
                [doot.structs.TaskSpec.build(y) for y in tail])


    def test_basic(self):
        obj = NaiveTracker()
        assert(isinstance(obj, NaiveTracker))


    def test_empty(self):
        obj = NaiveTracker()
        result = obj.generate_plan()
        assert(len(result) == 0)


    def test_simple_plan_dfs(self, specs):
        """ Generate a plan by dfs """
        expectation = [
            "basic::alpha",
            "basic::dep.1",
            "basic::dep.2",
            "basic::dep.4",
            "basic::dep.2",
            "basic::alpha",
            "basic::beta",
            "basic::dep.3",
            "basic::beta",
        ]
        head, tail = specs
        obj      = NaiveTracker()
        obj.register_spec(*head, *tail)
        t1_name = obj.queue_entry(head[0].name, from_user=True)
        t2_name = obj.queue_entry(head[1].name, from_user=True)
        assert(obj.get_status(t1_name) is TaskStatus_e.INIT)
        assert(obj.get_status(t2_name) is TaskStatus_e.INIT)
        obj.build_network()
        result = obj.generate_plan()
        assert(len(result) == len(expectation))
        for x,y in zip(result, expectation):
            expected_name = doot.structs.TaskName(y)
            assert(expected_name < x[1])


    def test_simple_plan_bfs(self, specs):
        expectation = [
            "basic::alpha",
            "basic::beta",
            "basic::dep.1",
            "basic::dep.2",
            "basic::dep.3",
            "basic::dep.4",
            "basic::dep.1",
            "basic::dep.3",
            "basic::beta",
            "basic::dep.4",
            "basic::dep.2",
            "basic::alpha",
            ]
        head, tail = specs
        obj      = NaiveTracker()
        obj.register_spec(*head, *tail)
        t1_name = obj.queue_entry(head[0].name, from_user=True)
        t2_name = obj.queue_entry(head[1].name, from_user=True)
        assert(obj.get_status(t1_name) is TaskStatus_e.INIT)
        assert(obj.get_status(t2_name) is TaskStatus_e.INIT)
        obj.build_network()
        result = obj.generate_plan(policy=ExecutionPolicy_e.BREADTH)
        assert(len(result) == len(expectation))
        for x,y in zip(result, expectation):
            expected_name = doot.structs.TaskName(y)
            assert(expected_name < x[1])
