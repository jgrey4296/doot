#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN202, ANN001, B011
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
from doot.workflow._interface import TaskStatus_e, TaskSpec_i, TaskMeta_e
from doot.util._interface import DelayedSpec
from doot.util import mock_gen
from ..naive_tracker import NaiveTracker
from .. import _interface as API  # noqa: N812
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
logging                                                      = logmod.root
logmod.getLogger("jgdv").propagate                           = False
logmod.getLogger("doot.util.factory").propagate              = False
logmod.getLogger("doot.control.tracker.registry").propagate  = False
logmod.getLogger("doot.control.tracker.queue").propagate     = False
logmod.getLogger("doot.control.tracker.network").propagate   = False
logmod.getLogger("doot.control.tracker._base").propagate     = False
logmod.getLogger("doot.workflow.task").propagate             = False


class TestTracker:

    @pytest.fixture(scope="function")
    def tracker(self):
        return NaiveTracker()

    def test_sanity(self):
        assert(True)
        assert(not False)

    def test_ctor(self):
        assert(isinstance(NaiveTracker, API.TaskTracker_p))

    def test_basic(self, tracker):
        assert(isinstance(tracker, NaiveTracker))

    def test_next_for_empty(self, tracker):
        tracker.build()
        assert(tracker.next_for() is None)

    def test_queued_with_no_connections_errors(self, tracker):
        spec = tracker._factory.build({"name":"basic::Task"})
        tracker.register(spec)
        instance = tracker.queue(spec.name)
        assert(instance.uuid())
        assert(tracker.get_status(target=instance)[0] is TaskStatus_e.DECLARED)
        tracker.build()
        with pytest.raises(doot.errors.TrackingError):
            tracker.validate()

    def test_next_simple(self, tracker):
        spec = tracker._factory.build({"name":"basic::alpha"})
        tracker.register(spec)
        instance = tracker.queue(spec.name, from_user=True)
        assert(bool(tracker._queue))
        assert(instance.uuid())
        assert(tracker.get_status(target=instance)[0] is TaskStatus_e.DECLARED)
        tracker.build()
        tracker.validate()
        match tracker.next_for():
            case Task_p() as result:
                assert(spec.name < result.name)
                assert(True)
            case _:
                assert(False)
        assert(tracker.get_status(target=instance)[0] is TaskStatus_e.RUNNING)


    def test_next_simple_dependency(self, tracker):
        spec = tracker._factory.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = tracker._factory.build({"name":"basic::dep"})
        tracker.register(spec, dep)
        instance = tracker.queue(spec.name, from_user=True)
        assert(tracker.get_status(target=instance)[0] is TaskStatus_e.DECLARED)
        tracker.build()
        tracker.validate()
        match tracker.next_for():
            case Task_p() as result:
                assert(dep.name < result.name)
                assert(True)
            case _:
                assert(False)
        assert(tracker.get_status(target=instance)[0] is TaskStatus_e.WAIT)

    def test_next_dependency_success_produces_ready_state_(self, tracker):
        spec = tracker._factory.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = tracker._factory.build({"name":"basic::dep"})
        tracker.register(spec, dep)
        instance = tracker.queue(spec.name, from_user=True)
        assert(tracker.get_status(target=instance)[0] is TaskStatus_e.DECLARED)
        tracker.build()
        dep_inst = tracker.next_for()
        assert(dep.name < dep_inst.name)
        tracker.set_status(dep_inst.name, TaskStatus_e.SUCCESS)
        match tracker.next_for():
            case Task_p() as result:
                assert(spec.name < result.name)
                assert(True)
            case _:
                assert(False)
        assert(tracker.get_status(target=instance)[0] is TaskStatus_e.RUNNING)

    def test_next_artificial_success(self, tracker):
        spec = tracker._factory.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = tracker._factory.build({"name":"basic::dep"})
        tracker.register(spec, dep)
        instance = tracker.queue(spec.name, from_user=True)
        dep_inst = tracker.queue(dep.name)
        tracker.build()
        assert(dep_inst in tracker._network.pred[instance])
        tracker._instantiate(dep_inst, task=True)
        # Force the dependency to success without getting it from next_for:
        tracker.set_status(dep_inst, TaskStatus_e.SUCCESS)
        assert(tracker.get_status(target=dep_inst)[0] is TaskStatus_e.SUCCESS)
        match tracker.next_for():
            case Task_p() as result:
                assert(spec.name < result.name)
                assert(True)
            case _:
                assert(False)
        assert(tracker.get_status(target=instance)[0] is TaskStatus_e.RUNNING)

class TestTracker_failing:

    @pytest.fixture(scope="function")
    def tracker(self):
        return NaiveTracker()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_next_fail(self, tracker):
        """
        fail all tasks, and only cleanups will be run
        """
        spec = tracker._factory.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = tracker._factory.build({"name":"basic::dep"})
        tracker.register(spec, dep)
        instance   = tracker.queue(spec.name, from_user=True)
        dep_inst = tracker.queue(dep.name)
        assert(tracker.get_status(target=instance)[0] is TaskStatus_e.DECLARED)
        logging.info("--------------------------------------------------")
        tracker.build()
        logging.info("--------------------------------------------------")
        # Instatiate the tasks so they can have status
        tracker._instantiate(instance, task=True)
        tracker._instantiate(dep_inst, task=True)
        # Force the dependency to fail without getting it from next_for:
        tracker.set_status(instance, TaskStatus_e.FAILED)
        tracker.set_status(dep_inst, TaskStatus_e.FAILED)
        assert(tracker.get_status(target=instance)[0] is TaskStatus_e.FAILED)
        assert(tracker.get_status(target=dep_inst)[0] is TaskStatus_e.FAILED)
        logging.info("--------------------------------------------------")
        match (current:=tracker.next_for()):
            case Task_p() as task:
                assert(task.name.is_cleanup())
            case x:
                assert(False), x
        ##--|
        accept_states = [TaskStatus_e.DEAD, TaskStatus_e.TEARDOWN]
        for name, _meta in tracker.specs.items():
            if name.uuid() or name.is_cleanup():
                continue
            if tracker.get_status(target=instance)[0] not in accept_states:
                # breakpoint()
                # pass
                assert(False)

class TestTracker_halting:

    @pytest.fixture(scope="function")
    def tracker(self):
        return NaiveTracker()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_next_halt(self, tracker):
        """ halting all tasks should """
        spec = tracker._factory.build({"name":"basic::alpha", "depends_on":["basic::dep"]})
        dep  = tracker._factory.build({"name":"basic::dep"})
        tracker.register(spec, dep)
        instance   = tracker.queue(spec.name, from_user=True)
        dep_inst = tracker.queue(dep.name)
        assert(tracker.get_status(target=instance)[0] is TaskStatus_e.DECLARED)
        logging.info("--------------------------------------------------")
        tracker.build()
        logging.info("--------------------------------------------------")
        # Force the dependency to success without getting it from next_for:
        tracker._instantiate(instance, task=True)
        tracker._instantiate(dep_inst, task=True)
        tracker.set_status(instance, TaskStatus_e.HALTED)
        tracker.set_status(dep_inst, TaskStatus_e.HALTED)
        logging.info("--------------------------------------------------")
        match tracker.next_for():
            case Task_p() as task:
                assert(task.name.is_cleanup())
            case x:
                assert(False), x
        ##--|
        accept_states = [TaskStatus_e.HALTED, TaskStatus_e.DEAD, TaskStatus_e.TEARDOWN]
        for name, _meta in tracker.specs.items():
            if not name.uuid() or name.is_cleanup():
                # Every abstract spec and cleanup is good
                continue
            # everything else should be finished
            match _meta.task:
                case TaskStatus_e() as x if x in accept_states:
                    assert(True)
                case Task_p() as t if t.status in accept_states:
                    assert(True)
                case x:
                    assert(False), x

class TestTracker_jobs:

    @pytest.fixture(scope="function")
    def tracker(self):
        return NaiveTracker()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_next_job_head(self, tracker):
        job_spec  = tracker._factory.build({"name":"basic::job", "meta": ["JOB"], "cleanup":["basic::task"]})
        task_spec = tracker._factory.build({"name":"basic::task", "test_key": "bloo"})
        tracker.register(job_spec)
        tracker.register(task_spec)
        instance = tracker.queue(job_spec, from_user=True)
        assert(job_spec.name in tracker.concrete)
        tracker.build()
        assert(bool(tracker._queue.active_set))
        assert(tracker.is_valid)
        # head is in network
        match tracker.next_for():
            case Task_p() as task:
                assert(job_spec.name < task.name)
                tracker.set_status(task.name, TaskStatus_e.SUCCESS)
                assert(tracker.is_valid)
            case x:
                assert(False), x

        match tracker.next_for():
            case Task_p() as task:
                assert(job_spec.name < task.name)
                assert(instance < task.name)
                assert(task.name.is_head())
                tracker.set_status(task.name, TaskStatus_e.SUCCESS)
                assert(tracker.is_valid)
                # A new job head hasn't been built
                assert(len(tracker.specs[job_spec.name].related) == 1)
            case x:
                assert(False), x

        match tracker.next_for():
            case Task_p():
                assert(True)
            case x:
                assert(False), x

    def test_next_job_head_with_subtasks(self, tracker):
        """ artificially run a job """
        logmod.getLogger("doot.control.tracker.network").propagate   = True
        job_spec  = tracker._factory.build({"name":"basic::+.job"})
        assert(TaskMeta_e.JOB in job_spec.meta)
        tracker.register(job_spec)
        instance = tracker.queue(job_spec, from_user=True)
        assert(job_spec.name in tracker.concrete)
        tracker.build()
        assert(bool(tracker._queue.active_set))
        job_body = tracker.next_for()
        assert(job_body.name == instance)
        logging.debug("-------------------------")
        # Add Tasks that the body generates:
        sub_spec1 = tracker._factory.build({"name":"basic::task.1", "test_key": "bloo", "required_for": [instance.with_head()]})
        sub_spec2 = tracker._factory.build({"name":"basic::task.2", "test_key": "blah", "required_for": [instance.with_head()]})
        ss1_inst = tracker.queue(sub_spec1)
        ss2_inst = tracker.queue(sub_spec2)
        tracker.build(sources=True)
        tracker.validate()
        # Artificially set priority of job body to force handling its success
        job_body.priority = 11
        tracker._queue._queue.add(job_body.name, priority=job_body.priority)
        tracker.set_status(instance, TaskStatus_e.SUCCESS)
        match tracker.next_for():
            case Task_p() as result:
                # Next task is one of the new subtasks
                assert(any(x < result.name for x in [sub_spec1.name, sub_spec2.name]))
            case x:
                assert(False), x


class TestTracker_cleanup:

    @pytest.fixture(scope="function")
    def tracker(self):
        return NaiveTracker()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_cleanup_shares_spec(self, tracker):
        tracker       = NaiveTracker()
        spec      = tracker._factory.build({"name":"basic::task", "cleanup":[{"do":"log", "msg":"{blah}"}], "blah":"aweg"})
        tracker.register(spec)
        tracker.queue(spec, from_user=True)
        tracker.build()
        match tracker.next_for():
            case Task_p() as task:
                assert("basic::task" < task.name)
                assert(task.internal_state["blah"] == "aweg")
                tracker.set_status(task.name, internal_state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match tracker.next_for():
            case Task_p() as task2:
                assert(task2.name.is_cleanup())
                assert(task2.internal_state["blah"] == "aweg")
            case x:
                 assert(False), x

    def test_cleanup_shares_state(self, tracker):
        spec      = tracker._factory.build({"name":"basic::task", "cleanup":[]})
        tracker.register(spec)
        instance = tracker.queue(spec, from_user=True)
        tracker.build()
        match tracker.next_for():
            case Task_p() as task:
                assert(spec.name < task.name)
                assert("blah" not in task.internal_state)
                task.internal_state["blah"] = "aweg"
                tracker.set_status(task.name, internal_state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match tracker.next_for():
            case Task_p() as task2:
                assert(task2.name.is_cleanup())
                assert(task2.internal_state["blah"] == "aweg")
            case x:
                 assert(False), x

    def test_cleanup_shares_state_to_deps(self, tracker):
        spec      = tracker._factory.build({"name":"basic::task", "cleanup":[{"task":"basic::dep", "inject":{"from_state": ["blah"]}}]})
        dep = tracker._factory.build({"name":"basic::dep"})
        tracker.register(spec, dep)
        tracker.queue(spec, from_user=True)
        tracker.build()
        match tracker.next_for():
            case Task_p() as task:
                assert("basic::task" < task.name)
                assert("blah" not in task.internal_state)
                task.internal_state["blah"] = "aweg"
                tracker.set_status(task.name, internal_state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match tracker.next_for():
            case Task_p() as task2:
                assert(dep.name < task2.name)
                assert(task2.internal_state["blah"] == "aweg")
                tracker.set_status(task2.name, internal_state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match tracker.next_for():
            case Task_p() as task3:
                assert(task3.name.is_cleanup())
                assert(task3.internal_state["blah"] == "aweg")
            case x:
                 assert(False), x

    def test_cleanup_shares_to_deps_cleanup(self, tracker):
        spec      = tracker._factory.build({"name":"basic::task", "cleanup":[{"task":"basic::dep", "inject":{"from_state": ["blah"]}}]})
        dep = tracker._factory.build({"name":"basic::dep"})
        tracker.register(spec, dep)
        tracker.queue(spec, from_user=True)
        tracker.build()
        match tracker.next_for():
            case Task_p() as task:
                assert("basic::task" < task.name)
                assert("blah" not in task.internal_state)
                task.internal_state["blah"] = "aweg"
                tracker.set_status(task.name, internal_state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match tracker.next_for():
            case Task_p() as task2:
                assert(dep.name < task2.name)
                assert(task2.internal_state["blah"] == "aweg")
                task2.internal_state['aweg'] = "qqqq"
                tracker.set_status(task2.name, internal_state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match tracker.next_for():
            case Task_p() as task3:
                assert(task3.name.is_cleanup())
                assert(task3.internal_state["blah"] == "aweg")
                assert("aweg" not in task3.internal_state)
            case x:
                 assert(False), x

        match tracker.next_for():
            case Task_p() as task4:
                assert(task4.name.is_cleanup())
                assert(dep.name < task4.name)
                assert(task4.internal_state['blah'] == "aweg")
                assert("aweg" in task4.internal_state)
            case x:
                 assert(False), x

    def test_cleanup_dep_must_injects(self, tracker):
        spec      = tracker._factory.build({"name":"basic::task", "cleanup":[{"task":"basic::dep", "inject":{"from_state": ["blah"]}}]})
        dep = tracker._factory.build({"name":"basic::dep", "must_inject": ["blah"]})
        tracker.register(spec, dep)
        tracker.queue(spec, from_user=True)
        tracker.build()
        match tracker.next_for():
            case Task_p() as task:
                assert("basic::task" < task.name)
                assert("blah" not in task.internal_state)
                task.internal_state["blah"] = "aweg"
                tracker.set_status(task.name, internal_state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match tracker.next_for():
            case Task_p() as task2:
                assert("basic::dep" < task2.name)
                assert(task2.internal_state["blah"] == "aweg")
                task2.internal_state['aweg'] = "qqqq"
                task2.internal_state["qqqq"] = "blah"
                tracker.set_status(task2.name, internal_state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match tracker.next_for():
            case Task_p() as task3:
                assert("basic::task" < task3.name)
                assert(task3.name.is_cleanup())
                assert(task3.internal_state["blah"] == "aweg")
                assert("aweg" not in task3.internal_state)
                assert("qqqq" not in task3.internal_state)
            case x:
                 assert(False), x

        match tracker.next_for():
            case Task_p() as task4:
                assert("basic::dep" < task4.name)
                assert(task4.name.is_cleanup())
                assert(task4.internal_state['blah'] == "aweg")
                assert(task4.internal_state["aweg"] == "qqqq")
                assert(task4.internal_state["qqqq"] == "blah")
            case x:
                 assert(False), x

    def test_cleanup_injections(self, tracker):
        spec  = tracker._factory.build({"name":"basic::task", "cleanup":[{"task":"basic::dep", "inject":{"from_state": ["blah"]}}]})
        dep   = tracker._factory.build({"name":"basic::dep", "must_inject": ["blah"]})
        tracker.register(spec, dep)
        tracker.queue(spec, from_user=True)
        tracker.build()
        match tracker.next_for():
            case Task_p() as task:
                assert("basic::task" < task.name)
                assert("blah" not in task.internal_state)
                task.internal_state["blah"] = "aweg"
                tracker.set_status(task.name, internal_state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match tracker.next_for():
            case Task_p() as task2:
                assert("basic::dep" < task2.name)
                assert(task2.internal_state["blah"] == "aweg")
                task2.internal_state['aweg'] = "qqqq"
                task2.internal_state["qqqq"] = "blah"
                tracker.set_status(task2.name, internal_state=TaskStatus_e.SUCCESS)
            case x:
                 assert(False), x

        match tracker.next_for():
            case Task_p() as task3:
                assert("basic::task" < task3.name)
                assert(task3.name.is_cleanup())
                assert(task3.internal_state["blah"] == "aweg")
                assert("aweg" not in task3.internal_state)
                assert("qqqq" not in task3.internal_state)
            case x:
                 assert(False), x

        match tracker.next_for():
            case Task_p() as task4:
                assert("basic::dep" < task4.name)
                assert(task4.name.is_cleanup())
                assert(task4.internal_state['blah'] == "aweg")
                assert(task4.internal_state["aweg"] == "qqqq")
                assert(task4.internal_state["qqqq"] == "blah")
            case x:
                 assert(False), x

class TestTracker_delayed:

    @pytest.fixture(scope="function")
    def tracker(self):
        return NaiveTracker()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_make_delayed(self, tracker):
        assert(isinstance(tracker, NaiveTracker))

        match tracker._factory.delay(base="blah::bloo", target="blah::bloo..custom", overrides={}):
            case DelayedSpec() as obj:
                assert(obj.base == "blah::bloo")
                assert(obj.target == "blah::bloo..custom")
            case x:
                assert(False), x

    def test_upgrade_delayed(self, tracker):
        delayed = tracker._factory.delay(base="blah::bloo", target="blah::bloo..custom", overrides={})
        base_spec = tracker._factory.build({"name":"blah::bloo", "value":25})
        tracker.register(base_spec)
        assert(len(tracker.specs) == 1)
        match tracker._upgrade_delayed_to_actual(delayed):
            case TaskSpec_i() as actual:
                assert(delayed.target <= actual.name)
                assert(actual.value == base_spec.value)
            case x:
                assert(False), x
