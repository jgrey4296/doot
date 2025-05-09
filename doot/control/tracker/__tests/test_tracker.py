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
import networkx as nx

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.workflow._interface import TaskStatus_e
from doot.util import mock_gen
from ..tracker import Tracker
from doot.workflow.structs.task_spec import TaskSpec
from doot.workflow.structs.task_name import TaskName

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

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|
from doot.workflow._interface import Task_p
# isort: on
# ##-- end types
logging = logmod.root

class TestSplitTracker:

    def test_sanity(self):
        assert(True)
        assert(not False)

    def test_basic(self):
        obj = Tracker()
        assert(isinstance(obj, Tracker))

    def test_next_for_fails_with_unbuilt_network(self):
        obj = Tracker()
        with pytest.raises(doot.errors.TrackingError) as ctx:
            obj.next_for()

        assert(ctx.value.args[0] == "Network is in an invalid state")

    def test_next_for_empty(self):
        obj = Tracker()
        obj.build_network()
        assert(obj.next_for() is None)

    def test_next_for_no_connections(self):
        obj  = Tracker()
        spec = TaskSpec.build({"name":"basic::Task"})
        obj.register_spec(spec)
        t_name = obj.queue_entry(spec.name)
        assert(t_name.is_uniq())
        assert(obj.get_status(t_name) is TaskStatus_e.DECLARED)
        obj.build_network()
        match obj.next_for():
            case Task_p():
                assert(True)
            case x:
                 assert(False), x
        assert(obj.get_status(t_name) is TaskStatus_e.RUNNING)

    def test_next_simple_dependendency(self):
        obj  = Tracker()
        spec = TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name = obj.queue_entry(spec.name, from_user=True)
        assert(obj.get_status(t_name) is TaskStatus_e.DECLARED)
        obj.build_network()
        match obj.next_for():
            case Task_p() as result:
                assert(dep.name < result.name)
                assert(True)
            case _:
                assert(False)
        assert(obj.get_status(t_name) is TaskStatus_e.WAIT)

    def test_next_dependency_success_produces_ready_state_(self):
        obj  = Tracker()
        spec = TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name = obj.queue_entry(spec.name, from_user=True)
        assert(obj.get_status(t_name) is TaskStatus_e.DECLARED)
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
        obj  = Tracker()
        spec = TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name   = obj.queue_entry(spec.name)
        dep_inst = obj.queue_entry(dep.name)
        assert(obj.get_status(t_name) is TaskStatus_e.DECLARED)
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
        obj  = Tracker()
        spec = TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name   = obj.queue_entry(spec.name, from_user=True)
        dep_inst = obj.queue_entry(dep.name)
        assert(obj.get_status(t_name) is TaskStatus_e.DECLARED)
        logging.info("--------------------------------------------------")
        obj.build_network()
        logging.info("--------------------------------------------------")
        # Force the dependency to success without getting it from next_for:
        obj._registry._make_task(t_name)
        obj._registry._make_task(dep_inst)
        obj.set_status(t_name, TaskStatus_e.HALTED)
        obj.set_status(dep_inst, TaskStatus_e.HALTED)
        logging.info("--------------------------------------------------")
        match obj.next_for():
            case Task_p() as task:
                assert(task.name.is_cleanup())
            case x:
                assert(False), x

        for x in obj._registry.tasks.values():
            if x.name.is_cleanup():
                continue
            assert(x.status in [TaskStatus_e.HALTED, TaskStatus_e.DEAD, TaskStatus_e.TEARDOWN])

    def test_next_fail(self):
        obj  = Tracker()
        spec = TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        t_name   = obj.queue_entry(spec.name, from_user=True)
        dep_inst = obj.queue_entry(dep.name)
        assert(obj.get_status(t_name) is TaskStatus_e.DECLARED)
        logging.info("--------------------------------------------------")
        obj.build_network()
        logging.info("--------------------------------------------------")
        # Force the dependency to success without getting it from next_for:
        obj._registry._make_task(t_name)
        obj._registry._make_task(dep_inst)
        obj.set_status(t_name, TaskStatus_e.FAILED)
        obj.set_status(dep_inst, TaskStatus_e.FAILED)
        logging.info("--------------------------------------------------")
        match (current:=obj.next_for()):
            case Task_p() as task:
                assert(task.name.is_cleanup())
            case x:
                assert(False), x

        for x in obj._registry.tasks.values():
            if x.name.is_cleanup():
                continue
            assert(x.status in [TaskStatus_e.DEAD, TaskStatus_e.TEARDOWN])

    def test_next_job_head(self):
        obj       = Tracker()
        job_spec  = TaskSpec.build({"name":"basic::job", "meta": ["JOB"], "cleanup":["basic::task"]})
        task_spec = TaskSpec.build({"name":"basic::task", "test_key": "bloo"})
        obj.register_spec(job_spec)
        obj.register_spec(task_spec)
        obj.queue_entry(job_spec, from_user=True)
        assert(job_spec.name in obj._registry.concrete)
        obj.build_network()
        assert(bool(obj._queue.active_set))
        assert(obj._network.is_valid)
        # head is in network
        match obj.next_for():
            case Task_p() as task:
                assert(job_spec.name < task.name)
                obj.set_status(task.name, TaskStatus_e.SUCCESS)
                assert(obj._network.is_valid)
            case x:
                assert(False), x

        match obj.next_for():
            case Task_p() as task:
                assert(job_spec.name.with_head() < task.name)
                assert(task.name.is_head())
                obj.set_status(task.name, TaskStatus_e.SUCCESS)
                assert(obj._network.is_valid)
                # A new job head hasn't been built
                assert(len(obj._registry.concrete[job_spec.name.with_head()]) == 1)
            case x:
                assert(False), x

        match obj.next_for():
            case Task_p():
                assert(True)
            case x:
                assert(False), x

    def test_next_job_head_with_subtasks(self):
        obj       = Tracker()
        job_spec  = TaskSpec.build({"name":"basic::job", "meta": ["JOB"]})
        sub_spec1 = TaskSpec.build({"name":"basic::task.1", "test_key": "bloo", "required_for": ["basic::job.$head$"]})
        sub_spec2 = TaskSpec.build({"name":"basic::task.2", "test_key": "blah", "required_for": ["basic::job.$head$"]})
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


class TestTrackingStates:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_cleanup_shares_spec(self):
        obj       = Tracker()
        spec      = TaskSpec.build({"name":"basic::task", "cleanup":[{"do":"log", "msg":"{blah}"}], "blah":"aweg"})
        obj.register_spec(spec)
        obj.queue_entry(spec, from_user=True)
        obj.build_network()
        match obj.next_for():
            case Task_p() as task:
                assert("basic::task" < task.name)
                assert(task.state["blah"] == "aweg")
                obj.set_status(task, state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match obj.next_for():
            case Task_p() as task2:
                assert(task2.name.is_cleanup())
                assert(task2.state["blah"] == "aweg")
            case x:
                 assert(False), x


    def test_cleanup_shares_state(self):

        obj       = Tracker()
        spec      = TaskSpec.build({"name":"basic::task", "cleanup":[]})
        obj.register_spec(spec)
        obj.queue_entry(spec, from_user=True)
        obj.build_network()
        match obj.next_for():
            case Task_p() as task:
                assert("basic::task" < task.name)
                assert("blah" not in task.state)
                task.state["blah"] = "aweg"
                obj.set_status(task, state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match obj.next_for():
            case Task_p() as task2:
                assert(task2.name.is_cleanup())
                assert(task2.state["blah"] == "aweg")
            case x:
                 assert(False), x


    def test_cleanup_shares_state_to_deps(self):

        obj       = Tracker()
        spec      = TaskSpec.build({"name":"basic::task", "cleanup":[{"task":"basic::dep", "inject":{"from_state": ["blah"]}}]})
        dep = TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        obj.queue_entry(spec, from_user=True)
        obj.build_network()
        match obj.next_for():
            case Task_p() as task:
                assert("basic::task" < task.name)
                assert("blah" not in task.state)
                task.state["blah"] = "aweg"
                obj.set_status(task, state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match obj.next_for():
            case Task_p() as task2:
                assert(dep.name < task2.name)
                assert(task2.state["blah"] == "aweg")
                obj.set_status(task2, state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match obj.next_for():
            case Task_p() as task3:
                assert(task3.name.is_cleanup())
                assert(task3.state["blah"] == "aweg")
            case x:
                 assert(False), x


    def test_cleanup_shares_to_deps_cleanup(self):

        obj       = Tracker()
        spec      = TaskSpec.build({"name":"basic::task", "cleanup":[{"task":"basic::dep", "inject":{"from_state": ["blah"]}}]})
        dep = TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, dep)
        obj.queue_entry(spec, from_user=True)
        obj.build_network()
        match obj.next_for():
            case Task_p() as task:
                assert("basic::task" < task.name)
                assert("blah" not in task.state)
                task.state["blah"] = "aweg"
                obj.set_status(task, state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match obj.next_for():
            case Task_p() as task2:
                assert(dep.name < task2.name)
                assert(task2.state["blah"] == "aweg")
                task2.state['aweg'] = "qqqq"
                obj.set_status(task2, state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match obj.next_for():
            case Task_p() as task3:
                assert(task3.name.is_cleanup())
                assert(task3.state["blah"] == "aweg")
                assert("aweg" not in task3.state)
            case x:
                 assert(False), x

        match obj.next_for():
            case Task_p() as task4:
                assert(task4.name.is_cleanup())
                assert(dep.name < task4.name)
                assert(task4.state['blah'] == "aweg")
                assert("aweg" in task4.state)
            case x:
                 assert(False), x


    def test_cleanup_dep_must_injects(self):

        obj       = Tracker()
        spec      = TaskSpec.build({"name":"basic::task", "cleanup":[{"task":"basic::dep", "inject":{"from_state": ["blah"]}}]})
        dep = TaskSpec.build({"name":"basic::dep", "must_inject": ["blah"]})
        obj.register_spec(spec, dep)
        obj.queue_entry(spec, from_user=True)
        obj.build_network()
        match obj.next_for():
            case Task_p() as task:
                assert("basic::task" < task.name)
                assert("blah" not in task.state)
                task.state["blah"] = "aweg"
                obj.set_status(task, state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match obj.next_for():
            case Task_p() as task2:
                assert("basic::dep" < task2.name)
                assert(task2.state["blah"] == "aweg")
                task2.state['aweg'] = "qqqq"
                task2.state["qqqq"] = "blah"
                obj.set_status(task2, state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match obj.next_for():
            case Task_p() as task3:
                assert("basic::task" < task3.name)
                assert(task3.name.is_cleanup())
                assert(task3.state["blah"] == "aweg")
                assert("aweg" not in task3.state)
                assert("qqqq" not in task3.state)
            case x:
                 assert(False), x

        match obj.next_for():
            case Task_p() as task4:
                assert("basic::dep" < task4.name)
                assert(task4.name.is_cleanup())
                assert(task4.state['blah'] == "aweg")
                assert(task4.state["aweg"] == "qqqq")
                assert(task4.state["qqqq"] == "blah")
            case x:
                 assert(False), x


    def test_cleanup_injections(self):

        obj       = Tracker()
        spec      = TaskSpec.build({"name":"basic::task", "cleanup":[{"task":"basic::dep", "inject":{"from_state": ["blah"]}}]})
        dep = TaskSpec.build({"name":"basic::dep", "must_inject": ["blah"]})
        obj.register_spec(spec, dep)
        obj.queue_entry(spec, from_user=True)
        obj.build_network()
        match obj.next_for():
            case Task_p() as task:
                assert("basic::task" < task.name)
                assert("blah" not in task.state)
                task.state["blah"] = "aweg"
                obj.set_status(task, state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match obj.next_for():
            case Task_p() as task2:
                assert("basic::dep" < task2.name)
                assert(task2.state["blah"] == "aweg")
                task2.state['aweg'] = "qqqq"
                task2.state["qqqq"] = "blah"
                obj.set_status(task2, state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match obj.next_for():
            case Task_p() as task3:
                assert("basic::task" < task3.name)
                assert(task3.name.is_cleanup())
                assert(task3.state["blah"] == "aweg")
                assert("aweg" not in task3.state)
                assert("qqqq" not in task3.state)
            case x:
                 assert(False), x

        match obj.next_for():
            case Task_p() as task4:
                assert("basic::dep" < task4.name)
                assert(task4.name.is_cleanup())
                assert(task4.state['blah'] == "aweg")
                assert(task4.state["aweg"] == "qqqq")
                assert(task4.state["qqqq"] == "blah")
            case x:
                 assert(False), x
