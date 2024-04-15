#!/usr/bin/env python3
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
import doot.structs
from doot.control.tracker import DootTracker
from doot._abstract import Task_i
from doot.utils import mock_gen

@pytest.mark.parametrize("ctor", [DootTracker])
class TestTrackerBasic:

    def test_initial(self, ctor):
        tracker = ctor()
        assert(tracker is not None)

    @pytest.mark.skip("TODO")
    def test_clear(self, ctor):
        pass

    @pytest.mark.skip("TODO")
    def test_validate(self, ctor):
        pass

    @pytest.mark.skip("TODO")
    def test_task_state(self, ctor):
        pass

    @pytest.mark.skip("TODO")
    def test_update_task_state(self, ctor):
        pass

@pytest.mark.parametrize("ctor", [DootTracker])
class TestTrackerArtifacts:

    @pytest.mark.xfail
    def test_task_exact_artifact_dependency(self, ctor, mocker):
        tracker = ctor()
        for task in mock_gen.task_network({"task1"     : [[pl.Path("test.file")], []],
                                           "subtask"   : [[], [pl.Path("blah.other")]],
                                           "subtask2"  : [[], [pl.Path("test.file")]],

                                          }):
            tracker.add_task(task)

        next_task = tracker.next_for("default::task1")
        assert(next_task.name == "default::subtask2")

    @pytest.mark.skip
    def test_task_inexact_artifact_dependency(self, ctor, mocker):
        tracker = ctor()
        for task in mock_gen.task_network({"task1"     : [[pl.Path("*.file")], []],
                                           "subtask"   : [[], [pl.Path("blah.other")]],
                                           "subtask2"  : [[], [pl.Path("test.file")]],

                                          }):
            tracker.add_task(task)

        next_task = tracker.next_for("default::task1")
        assert(isinstance(next_task, doot.structs.DootTaskArtifact))

    @pytest.mark.xfail
    def test_task_artifact_exists(self, ctor, mocker):
        """
          check that if artifacts exist, tasks that generate them aren't queued
        """
        mocker.patch.object(pl.Path, "exists", return_value=True)
        tracker = ctor()
        for task in mock_gen.task_network({"task1"     : [[pl.Path("*.file")], []],
                                           "subtask"   : [[], [pl.Path("blah.other")]],
                                           "subtask2"  : [[], [pl.Path("test.file")]],

                                          }):
            tracker.add_task(task)

        next_task = tracker.next_for("default::task1")
        assert(isinstance(next_task, doot.structs.DootTaskArtifact))

    @pytest.mark.skip
    def test_task_artifact_doesnt_exists(self, ctor, mocker):
        mocker.patch.object(pl.Path, "exists", return_value=False)
        tracker = ctor()
        for task in mock_gen.task_network({"task1"     : [[pl.Path("*.file")], []],
                                           "subtask"   : [[], [pl.Path("blah.other")]],
                                           "subtask2"  : [[], [pl.Path("test.file")]],

                                          }):
            tracker.add_task(task)

        next_task = tracker.next_for("default::task1")
        assert(isinstance(next_task, doot.structs.DootTaskArtifact))

    @pytest.mark.xfail
    def test_task_artifact_partial_exists(self, ctor, mocker):

        def temp_exists(self):
            return not "*" in self.stem

        mocker.patch.object(pl.Path, "exists", new=temp_exists)
        tracker = ctor()
        for task in mock_gen.task_network({"task1"     : [[pl.Path("*.file")], []],
                                           "subtask"   : [[], [pl.Path("blah.other")]],
                                           "subtask2"  : [[], [pl.Path("test.file")]],

                                          }):
            tracker.add_task(task)

        next_task = tracker.next_for("default::task1")
        assert(isinstance(next_task, doot.structs.DootTaskArtifact))

@pytest.mark.parametrize("ctor", [DootTracker])
class TestTrackerInsertion:

    def test_add_task(self, ctor, mocker):
        mock_task = mock_gen.mock_task("task1")
        tracker = ctor()
        tracker.add_task(mock_task)

        assert("default::task1" in tracker.tasks)
        assert(tracker.task_graph.nodes['default::task1']['state'] == tracker.state_e.DEFINED)

    def test_duplicate_add_fail(self, ctor, mocker):
        """ dont add a duplicately named task, or its dependencies """
        task1 = mock_gen.mock_task("task1")
        task2 = mock_gen.mock_task("task1")

        tracker = ctor()
        tracker.add_task(task1)
        with pytest.raises(doot.errors.DootTaskTrackingError):
            tracker.add_task(task2)

        assert("default::task1" in tracker.tasks)

    def test_duplicate_add(self, ctor, mocker):
        task1 = mock_gen.mock_task("task1")
        task2 = mock_gen.mock_task("task1")

        tracker = ctor(shadowing=True)
        tracker.add_task(task1)
        tracker.add_task(task2)

        assert("default::task1" in tracker.tasks)

    def test_warn_on_undefined(self, ctor, mocker, caplog):
        """ create a task with undefined dependencies, it should just warn not error """
        tracker = ctor()
        for task in mock_gen.task_network({"task1"     : [["subtask", "subtask2"], []]}):
            tracker.add_task(task)

        assert(tracker.next_for("default::task1").name == "default::task1")
        assert(bool([x for x in caplog.records if x.levelname == "WARNING"]))
        assert("Tried to Schedule a Declared but Undefined Task: subtask" in caplog.messages)
        assert("Tried to Schedule a Declared but Undefined Task: subtask2" in caplog.messages)

    @pytest.mark.skip
    def test_task_prior_registration(self, ctor, mocker):
        mock_task = mock_gen.mock_task("test_task")
        mock_task.spec.depends_on.append("example")
        mock_task.spec.depends_on.append("blah")

        tracker = ctor()
        tracker.add_task(mock_task)

        assert(tracker.task_graph.nodes['example']['state'] == tracker.state_e.DECLARED)
        assert(tracker.task_graph.nodes['blah']['state'] == tracker.state_e.DECLARED)
        assert("example" in tracker.task_graph)
        assert("blah" in tracker.task_graph)

    @pytest.mark.skip
    def test_task_post_registration(self, ctor, mocker):
        mock_task = mock_gen.mock_task("test_task")
        mock_task.required_for.append(doot.structs.DootTaskName.build("example"))
        mock_task.required_for.append(doot.structs.DootTaskName.build("blah"))

        tracker = ctor()
        tracker.add_task(mock_task)
        assert(tracker.task_graph.nodes['default::example']['state'] == tracker.state_e.DECLARED)
        assert(tracker.task_graph.nodes['default::blah']['state'] == tracker.state_e.DECLARED)
        assert("default::example" in tracker.task_graph)
        assert("default::blah" in tracker.task_graph)

    @pytest.mark.skip
    def test_declared_set(self, ctor, mocker):
        mock_task = mock_gen.mock_task("test_task")
        mock_task.depends_on   += map(doot.structs.DootTaskName.build, ["subtask", "sub2"])
        mock_task.required_for += map(doot.structs.DootTaskName.build, ["example", "blah"])

        tracker = ctor()
        tracker.add_task(mock_task)
        declared = tracker.declared_set()
        assert(declared == {"__root", "default::test_task", "default::subtask","default::sub2", "default::example", "default::blah"})

    def test_defined_set(self, ctor, mocker):
        mock_task = mock_gen.mock_task("test_task")

        tracker = ctor()
        tracker.add_task(mock_task)

        defined = tracker.defined_set()
        assert(defined == {"default::test_task"})

    def test_contains_defined(self, ctor, mocker):
        mock_task = mock_gen.mock_task("test_task")
        mock_task.depends_on = ["example", "blah"]

        tracker = ctor()
        tracker.add_task(mock_task)
        # defined Task is contained
        assert("default::test_task" in tracker)

    def test_not_contains_declared(self, ctor, mocker):
        mock_task = mock_gen.mock_task("test_task", pre=["example", "blah"])

        tracker = ctor()
        tracker.add_task(mock_task)
        assert("example" not in tracker)
        assert("blah" not in tracker)

    @pytest.mark.skip("TODO")
    def test_late_count(self, ctor):
        pass

@pytest.mark.parametrize("ctor", [DootTracker])
class TestTrackerUpdate:

    def test_task_order(self, ctor, mocker):
        tasks = mock_gen.task_network({
            "task1"   : [["default::subtask", "default::subtask2"], []],
            "subtask" : [["default::subsub"], []],
            "subtask2": [["default::subsub"], []],
            "subsub"  : [[], []]
         })

        tracker  = ctor()
        for task in tasks:
            tracker.add_task(task)

        next_task = tracker.next_for("default::task1")
        assert(next_task.name == "default::subsub")
        tracker.update_state(next_task, tracker.state_e.SUCCESS)

        next_task_2 = tracker.next_for()
        assert(next_task_2.name in {"default::subtask", "default::subtask2"})
        tracker.update_state(next_task_2, tracker.state_e.SUCCESS)

        next_task_3 = tracker.next_for()
        assert(next_task_3.name in {"default::subtask", "default::subtask2"} - {next_task_2.name})
        tracker.update_state(next_task_3, tracker.state_e.SUCCESS)

        next_task_4 = tracker.next_for()
        assert(next_task_4.name in "default::task1")

    def test_task_iter(self, ctor, mocker):
        tasks = mock_gen.task_network({
            "task1"   : [["default::subtask", "default::subtask2", "default::subtask3"], []],
            "subtask" : [["default::subsub"], []],
            "subtask2": [["default::subsub"], []],
            "subtask3": [["default::subsub"], []],
            "subsub"  : [[], []]
         })

        tasks[0].priority = 0

        tracker             = ctor()
        for task in tasks:
            tracker.add_task(task)

        result_tasks = []
        tracker.queue_task("default::task1")
        for x in tracker:
            if x:
                result_tasks.append(x.name)
                tracker.update_state(x.name, tracker.state_e.SUCCESS)

        assert(len(result_tasks) == 5)

    def test_task_iter_state_changed(self, ctor, mocker):
        tracker  = ctor()
        for task in mock_gen.task_network({"task1"   : [["default::subtask", "default::subtask2", "default::subtask3"], []],
                                           "subtask" : [["default::subsub"], []],
                                           "subtask2": [["default::subsub"], []],
                                           "subtask3": [["default::subsub"], []],
                                           "subsub"  : [[], []]
                                          }):
            tracker.add_task(task)

        tracker.update_state("default::subtask2", tracker.state_e.SUCCESS)
        tasks = []
        tracker.queue_task("default::task1")
        for x in tracker:
            if x:
                tasks.append(x.name)
                tracker.update_state(x.name, tracker.state_e.SUCCESS)

        assert("default::subtask2" not in tasks)
        assert(len(tasks) == 4)

    @pytest.mark.xfail
    def test_task_failure(self, ctor, mocker, caplog):
        tracker = ctor()
        for task in mock_gen.task_network({"task1"   : [["default::subtask"], []],
                                           "subtask" : [["default::subsub"], []],
                                          }):
            tracker.add_task(task)

        result = tracker.next_for("default::task1")
        assert(result.name == "default::subtask")
        tracker.update_state(result, tracker.state_e.SUCCESS)
        assert(tracker.next_for().name == "default::task1")
        assert("Tried to Schedule a Declared but Undefined Task: subsub" in caplog.messages)

    def test_post_task_order(self, ctor, mocker):
        tracker = ctor()
        for task in mock_gen.task_network({"task1"     : [["default::subtask", "default::subtask2"], []],
                                           "subtask"   : [["default::subsub"], ["default::sidesuper"]],
                                           "subtask2"  : [[], []],
                                           "subsub"    : [[], []],
                                           "sidesuper" : [[], []],

                                          }):
            tracker.add_task(task)

        next_task = tracker.next_for("default::task1")
        assert(next_task.name == "default::subtask2")
        tracker.update_state(next_task, tracker.state_e.SUCCESS)

        next_task_2 = tracker.next_for()
        assert(next_task_2.name == "default::subsub")
        tracker.update_state(next_task_2, tracker.state_e.SUCCESS)

        next_task_3 = tracker.next_for()
        assert(next_task_3.name == "default::subtask")
        tracker.update_state(next_task_3, tracker.state_e.SUCCESS)

        next_task_4 = tracker.next_for()
        assert(next_task_4.name == "default::task1" )

class TestTrackerPersistence:

    @pytest.mark.skip("TODO")
    def test_all_state(self):
        pass

    @pytest.mark.skip("TODO")
    def test_write(self):
        pass

    @pytest.mark.skip("TODO")
    def test_read(self):
        pass
