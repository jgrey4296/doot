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

# ##-- end 1st party imports

doot._test_setup()

# ##-- 1st party imports
import doot.errors
import doot.structs
from doot._abstract import Task_i
from doot.control.base_tracker import BaseTracker
from doot.control.tracker import DootTracker
from doot.enums import TaskStatus_e, ExecutionPolicy_e

# ##-- end 1st party imports

class TestTrackerNext:

    def test_basic(self):
        obj = DootTracker()
        assert(isinstance(obj, DootTracker))


    def test_next_for_fails_with_unbuilt_network(self):
        obj = DootTracker()
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.next_for()


    def test_next_for_empty(self):
        obj = DootTracker()
        obj.build_network()
        assert(obj.next_for() is None)


    def test_next_for_no_connections(self):
        obj  = DootTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::Task"})
        obj.register_spec(spec)
        t_name = obj.queue_entry(spec.name)
        assert(obj.get_status(t_name) is TaskStatus_e.default)
        obj.build_network()
        match obj.next_for():
            case Task_i():
                assert(True)
            case _:
                assert(False)
        assert(obj.get_status(t_name) is TaskStatus_e.RUNNING)


    def test_next_simple_dependendency(self):
        obj  = DootTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name = obj.queue_entry(spec.name, from_user=True)
        assert(obj.get_status(t_name) is TaskStatus_e.default)
        obj.build_network()
        match obj.next_for():
            case Task_i() as result:
                assert(dep.name < result.name)
                assert(True)
            case _:
                assert(False)
        assert(obj.get_status(t_name) is TaskStatus_e.WAIT)


    def test_next_dependency_success_produces_ready_state_(self):
        obj  = DootTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name = obj.queue_entry(spec.name, from_user=True)
        assert(obj.get_status(t_name) is TaskStatus_e.default)
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
        obj  = DootTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name   = obj.queue_entry(spec.name)
        dep_inst = obj.queue_entry(dep.name)
        assert(obj.get_status(t_name) is TaskStatus_e.default)
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
        obj  = DootTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name   = obj.queue_entry(spec.name, from_user=True)
        dep_inst = obj.queue_entry(dep.name)
        assert(obj.get_status(t_name) is TaskStatus_e.default)
        obj.build_network()
        # Force the dependency to success without getting it from next_for:
        obj.set_status(dep_inst, TaskStatus_e.HALTED)
        assert(obj.next_for() == None)
        assert(all(x.status == TaskStatus_e.HALTED for x in obj.tasks.values()))


    def test_next_fail(self):
        obj  = DootTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name   = obj.queue_entry(spec.name, from_user=True)
        dep_inst = obj.queue_entry(dep.name)
        assert(obj.get_status(t_name) is TaskStatus_e.default)
        obj.build_network()
        # Force the dependency to success without getting it from next_for:
        obj.set_status(dep_inst, TaskStatus_e.FAILED)
        assert(obj.next_for() == None)
        assert(all(x.status == TaskStatus_e.FAILED for x in obj.tasks.values()))

    def test_next_job_head(self):
        obj       = DootTracker()
        job_spec  = doot.structs.TaskSpec.build({"name":"basic::job", "flags": ["JOB"], "cleanup":["basic::task"]})
        task_spec = doot.structs.TaskSpec.build({"name":"basic::task", "test_key": "bloo"})
        obj.register_spec(job_spec)
        obj.register_spec(task_spec)
        obj.queue_entry(job_spec, from_user=True)
        assert(job_spec.name in obj.concrete)
        assert(job_spec.name.job_head() in obj.concrete)
        conc_job_body = obj.concrete[job_spec.name][-1]
        conc_job_head = obj.concrete[job_spec.name.job_head()][0]
        obj.build_network()
        assert(bool(obj.active_set))
        # head is in network
        assert(conc_job_head in obj.network.nodes)
        assert(obj.next_for().name == conc_job_body)
        obj.set_status(conc_job_body, TaskStatus_e.SUCCESS)
        result = obj.next_for()
        assert(job_spec.name.job_head() < result.name)
        obj.set_status(result.name, TaskStatus_e.SUCCESS)
        result = obj.next_for()
        assert(result is not None)
        # A new job head hasn't been built
        assert(len(obj.concrete[job_spec.name.job_head()]) == 1)


    def test_next_job_head_with_subtasks(self):
        obj       = DootTracker()
        job_spec  = doot.structs.TaskSpec.build({"name":"basic::job", "flags": ["JOB"]})
        sub_spec1 = doot.structs.TaskSpec.build({"name":"basic::task.1", "test_key": "bloo", "required_for": ["basic::job.$head$"]})
        sub_spec2 = doot.structs.TaskSpec.build({"name":"basic::task.2", "test_key": "blah", "required_for": ["basic::job.$head$"]})
        obj.register_spec(job_spec)
        obj.queue_entry(job_spec, from_user=True)
        assert(job_spec.name in obj.concrete)
        assert(job_spec.name.job_head() in obj.concrete)
        conc_job_body = obj.concrete[job_spec.name][-1]
        conc_job_head = obj.concrete[job_spec.name.job_head()][0]
        obj.build_network()
        assert(conc_job_head in obj.network.nodes)
        assert(bool(obj.active_set))
        job_body = obj.next_for()
        assert(job_body.name == conc_job_body)
        # Check head hasn't been added to network:
        assert(conc_job_head in obj.network.nodes)
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
            doot.structs.TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep.1", "basic::dep.2"]}),
            doot.structs.TaskSpec.build({"name":"basic::beta", "depends_on":["basic::dep.3"]}),
            doot.structs.TaskSpec.build({"name":"basic::solo", "depends_on":[]}),
        ]
        tail += [
            doot.structs.TaskSpec.build({"name":"basic::dep.1"}),
            doot.structs.TaskSpec.build({"name":"basic::dep.2"}),
            doot.structs.TaskSpec.build({"name":"basic::dep.3"}),
            doot.structs.TaskSpec.build({"name":"basic::dep.4", "required_for":["basic::dep.2"]}),
        ]
        return (head, tail)


    def test_basic(self):
        obj = DootTracker()
        assert(isinstance(obj, DootTracker))


    def test_empty(self):
        obj = DootTracker()
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
        obj      = DootTracker()
        obj.register_spec(*head, *tail)
        t1_name = obj.queue_entry(head[0].name, from_user=True)
        t2_name = obj.queue_entry(head[1].name, from_user=True)
        assert(obj.get_status(t1_name) is TaskStatus_e.default)
        assert(obj.get_status(t2_name) is TaskStatus_e.default)
        obj.build_network()
        result = obj.generate_plan()
        assert(len(result) == len(expectation))
        for x,y in zip(result, expectation):
            expected_name = doot.structs.TaskName.build(y)
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
        obj      = DootTracker()
        obj.register_spec(*head, *tail)
        t1_name = obj.queue_entry(head[0].name, from_user=True)
        t2_name = obj.queue_entry(head[1].name, from_user=True)
        assert(obj.get_status(t1_name) is TaskStatus_e.default)
        assert(obj.get_status(t2_name) is TaskStatus_e.default)
        obj.build_network()
        result = obj.generate_plan(policy=ExecutionPolicy_e.BREADTH)
        assert(len(result) == len(expectation))
        for x,y in zip(result, expectation):
            expected_name = doot.structs.TaskName.build(y)
            assert(expected_name < x[1])

    def test_simple_plan_priority(self, specs):
        expectation = [
            "basic::dep.4",
            "basic::dep.1",
            "basic::dep.3",
            "basic::dep.2",
            "basic::beta",
            "basic::alpha",
            ]
        head, tail = specs
        obj      = DootTracker()
        obj.register_spec(*head, *tail)
        t1_name = obj.queue_entry(head[0].name, from_user=True)
        t2_name = obj.queue_entry(head[1].name, from_user=True)
        assert(obj.get_status(t1_name) is TaskStatus_e.default)
        assert(obj.get_status(t2_name) is TaskStatus_e.default)
        obj.build_network()
        result = obj.generate_plan(policy=ExecutionPolicy_e.PRIORITY)
        assert(len(result) == len(expectation))
        for x,y in zip(result, expectation):
            expected_name = doot.structs.TaskName.build(y)
            assert(expected_name < x[1])


    @pytest.mark.xfail
    def test_simple_plan_priority_repeated(self, specs):
        """ TODO: fix indeterminacy of priority sorting """
        expectation = [
            "basic::dep.4",
            "basic::dep.1",
            "basic::dep.3",
            "basic::dep.2",
            "basic::beta",
            "basic::alpha",
            ]
        head, tail = specs
        obj      = DootTracker()
        obj.register_spec(*head, *tail)
        t1_name = obj.queue_entry(head[0].name, from_user=True)
        t2_name = obj.queue_entry(head[1].name, from_user=True)
        assert(obj.get_status(t1_name) is TaskStatus_e.default)
        assert(obj.get_status(t2_name) is TaskStatus_e.default)
        obj.build_network()

        original_tasks = set(obj.active_set)
        original_statuses : dict[Node, TaskStatus_e] = {x: obj.get_status(x) for x in itz.chain(obj.specs.keys(), obj.artifacts.keys())}

        for i in range(5):
            logging.warning("Starting to generate plan: %s", i)
            result = obj.generate_plan(policy=ExecutionPolicy_e.PRIORITY)
            assert(len(result) == len(expectation))
            for x,y in zip(result, expectation):
                expected_name = doot.structs.TaskName.build(y)
                assert(expected_name < x[1])

            assert(obj.active_set == original_tasks)
            post_statuses = {x: obj.get_status(x) for x in itz.chain(obj.specs.keys(), obj.artifacts.keys())}
            assert(all(k==k2 and x==y for (k,x),(k2,y) in zip(original_statuses.items(), post_statuses.items())))
