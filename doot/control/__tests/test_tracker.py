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
import doot.errors
import doot.structs
from doot.control.tracker import DootTracker
from doot._abstract import Task_i
from doot.utils import mock_gen

class TestTracker:

    def test_initial(self):
        tracker = DootTracker()
        assert(tracker is not None)

    def test_add_task(self, mocker):
        mock_task, depends_on, required_for = mock_gen.mock_task(mocker, "test_task")

        tracker = DootTracker()
        tracker.add_task(mock_task)

        assert("test_task" in tracker.tasks)
        assert(tracker.task_graph.nodes['test_task']['state'] == tracker.state_e.DEFINED)
        depends_on.assert_called()
        required_for.assert_called()

    def test_duplicate_add_fail(self, mocker):
        task1, pre1, post1 = mock_gen.mock_task(mocker, "task1")
        task2, pre2, post2 = mock_gen.mock_task(mocker, "task1")

        tracker = DootTracker()
        tracker.add_task(task1)
        with pytest.raises(doot.errors.DootTaskTrackingError):
            tracker.add_task(task2)

        assert("task1" in tracker.tasks)
        pre1.assert_called()
        pre1.assert_called()
        pre2.assert_not_called()
        post2.assert_not_called()

    def test_duplicate_add(self, mocker):
        task1, pre1, post1 = mock_gen.mock_task(mocker, "task1")
        task2, pre2, post2 = mock_gen.mock_task(mocker, "task1")

        tracker = DootTracker(shadowing=True)
        tracker.add_task(task1)
        tracker.add_task(task2)

        assert("task1" in tracker.tasks)
        pre1.assert_called()
        pre1.assert_called()
        pre2.assert_called()
        post2.assert_called()

    def test_contains_defined(self, mocker):
        mock_task, _, _= mock_gen.mock_task(mocker, "test_task")
        mock_task.depends_on = ["example", "blah"]

        tracker = DootTracker()
        tracker.add_task(mock_task)
        # defined Task is contained
        assert("test_task" in tracker)


    def test_warn_on_undefined(self, mocker, caplog):
        """ create a task with undefined dependencies, it should just warn not error """
        task1,    *_ = mock_gen.mock_task(mocker, "task1", pre=["subtask", "subtask2"])
        tracker = DootTracker()
        tracker.add_task(task1)

        assert(tracker.next_for("task1").name is "task1")

        assert(bool([x for x in caplog.records if x.levelname == "WARNING"]))
        assert("Tried to Schedule a Declared but Undefined Task: subtask" in caplog.messages)
        assert("Tried to Schedule a Declared but Undefined Task: subtask2" in caplog.messages)

    def test_not_contains_declared(self, mocker):
        mock_task, _, _= mock_gen.mock_task(mocker, "test_task", pre=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)
        assert("example" not in tracker)
        assert("blah" not in tracker)

    def test_task_prior_registration(self, mocker):
        mock_task, pre, post = mock_gen.mock_task(mocker, "test_task", pre=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)
        assert(tracker.task_graph.nodes['example']['state'] == tracker.state_e.DECLARED)
        assert(tracker.task_graph.nodes['blah']['state'] == tracker.state_e.DECLARED)
        assert("example" in tracker.task_graph)
        assert("blah" in tracker.task_graph)

    def test_task_post_registration(self, mocker):
        mock_task, *_ = mock_gen.mock_task(mocker, "test_task", post=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)
        assert(tracker.task_graph.nodes['example']['state'] == tracker.state_e.DECLARED)
        assert(tracker.task_graph.nodes['blah']['state'] == tracker.state_e.DECLARED)
        assert("example" in tracker.task_graph)
        assert("blah" in tracker.task_graph)

    def test_declared_set(self, mocker):
        mock_task, *_ = mock_gen.mock_task(mocker, "test_task", pre=["subtask", "sub2"], post=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)
        declared = tracker.declared_set()
        assert(declared == {"__root", "test_task", "subtask","sub2", "example", "blah"})

    def test_defined_set(self, mocker):
        mock_task, *_ = mock_gen.mock_task(mocker, "test_task", pre=["subtask", "sub2"], post=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)

        defined = tracker.defined_set()
        assert(defined == {"test_task"})

    def test_task_order(self, mocker):
        task1,    *_ = mock_gen.mock_task(mocker, "task1", pre=["subtask", "subtask2"])
        subtask,  *_ = mock_gen.mock_task(mocker, "subtask", pre=["subsub"])
        subtask2, *_ = mock_gen.mock_task(mocker, "subtask2", pre=["subsub"])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)

        next_task = tracker.next_for("task1")
        assert(next_task.name in {"subtask", "subtask2"})
        tracker.update_state(next_task, tracker.state_e.SUCCESS)
        next_task_2 = tracker.next_for()
        assert(next_task_2.name in {"subtask", "subtask2"} - {next_task.name})
        tracker.update_state(next_task_2, tracker.state_e.SUCCESS)
        next_task_3 = tracker.next_for()
        assert(next_task_3.name in "task1")

    def test_task_iter(self, mocker):
        task1,    *_ = mock_gen.mock_task(mocker, "task1", pre=["subtask", "subtask2", "subtask3"])
        subtask,  *_ = mock_gen.mock_task(mocker, "subtask", pre=["subsub"])
        subtask2, *_ = mock_gen.mock_task(mocker, "subtask2", pre=["subsub"])
        subtask3, *_ = mock_gen.mock_task(mocker, "subtask3", pre=["subsub"])

        task1.spec = mocker.Mock()
        task1.spec.priority = 0

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)
        tracker.add_task(subtask3)

        tasks = []
        tracker.queue_task("task1")
        for x in tracker:
            if x:
                tasks.append(x.name)
                tracker.update_state(x.name, tracker.state_e.SUCCESS)

        assert(len(tasks) == 4)

    def test_task_iter_state_changed(self, mocker):
        task1,    *_ = mock_gen.mock_task(mocker, "task1", pre=["subtask", "subtask2", "subtask3"])
        subtask,  *_ = mock_gen.mock_task(mocker, "subtask", pre=["subsub"])
        subtask2, *_ = mock_gen.mock_task(mocker, "subtask2", pre=["subsub"])
        subtask3, *_ = mock_gen.mock_task(mocker, "subtask3", pre=["subsub"])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)
        tracker.add_task(subtask3)

        tracker.update_state("subtask2", tracker.state_e.SUCCESS)
        tasks = []
        tracker.queue_task("task1")
        for x in tracker:
            if x:
                tasks.append(x.name)
                tracker.update_state(x.name, tracker.state_e.SUCCESS)

        assert("subtask2" not in tasks)
        assert(len(tasks) == 3)

    def test_task_failure(self, mocker, caplog):
        task1,    *_ = mock_gen.mock_task(mocker, "task1", pre=["subtask"])
        subtask,  *_ = mock_gen.mock_task(mocker, "subtask", pre=["subsub"])
        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)

        result = tracker.next_for("task1")
        assert(result.name == "subtask")
        tracker.update_state(result, tracker.state_e.SUCCESS)
        assert(tracker.next_for().name == "task1")
        assert("Tried to Schedule a Declared but Undefined Task: subsub" in caplog.messages)


    def test_post_task_order(self, mocker):
        task1,    *_  = mock_gen.mock_task(mocker, "task1", pre=["subtask", "subtask2"])
        subtask,  *_  = mock_gen.mock_task(mocker, "subtask", pre=["subsub"], post=["sidesuper"])
        sidesuper, *_ = mock_gen.mock_task(mocker, "sidesuper")
        subtask2 , *_ = mock_gen.mock_task(mocker, "subtask2")
        subsub   , *_ = mock_gen.mock_task(mocker, "subsub")

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(sidesuper)
        tracker.add_task(subtask2)
        tracker.add_task(subsub)

        next_task = tracker.next_for("task1")
        assert(next_task.name == "subtask2")
        tracker.update_state(next_task, tracker.state_e.SUCCESS)
        next_task_2 = tracker.next_for()
        assert(next_task_2.name == "subsub")
        tracker.update_state(next_task_2, tracker.state_e.SUCCESS)
        next_task_3 = tracker.next_for()
        assert(next_task_3.name == "subtask")
        tracker.update_state(next_task_3, tracker.state_e.SUCCESS)
        next_task_4 = tracker.next_for()
        assert(next_task_4.name == "task1" )

    def test_task_exact_artifact_dependency(self, mocker):
        task1,    *_ = mock_gen.mock_task(mocker, "task1",    pre=[pl.Path("test.file")])
        subtask,  *_ = mock_gen.mock_task(mocker, "subtask",  post=[pl.Path("blah.other")])
        subtask2, *_ = mock_gen.mock_task(mocker, "subtask2", post=[pl.Path("test.file")])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)
        next_task = tracker.next_for("task1")
        assert(next_task.name == "subtask2")

    def test_task_inexact_artifact_dependency(self, mocker):
        task1,    *_ = mock_gen.mock_task(mocker, "task1", pre=[pl.Path("*.file")])
        subtask,  *_ = mock_gen.mock_task(mocker, "subtask", post=[pl.Path("blah.other")])
        subtask2, *_ = mock_gen.mock_task(mocker, "subtask2", post=[pl.Path("test.file")])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)
        next_task = tracker.next_for("task1")
        assert(isinstance(next_task, doot.structs.DootTaskArtifact))

    def test_task_artifact_exists(self, mocker):
        """
          check that if artifacts exist, tasks that generate them aren't queued
        """
        mocker.patch.object(pl.Path, "exists", return_value=True)
        task1,    *_ = mock_gen.mock_task(mocker, "task1",    pre=[pl.Path("*.file")])
        subtask,  *_ = mock_gen.mock_task(mocker, "subtask",  post=[pl.Path("blah.other")])
        subtask2, *_ = mock_gen.mock_task(mocker, "subtask2", post=[pl.Path("test.file")])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)

        next_task = tracker.next_for("task1")
        assert(isinstance(next_task, doot.structs.DootTaskArtifact))

    def test_task_artifact_doesnt_exists(self, mocker):
        mocker.patch.object(pl.Path, "exists", return_value=False)
        task1,    *_ = mock_gen.mock_task(mocker, "task1", pre=[pl.Path("*.file")])
        subtask,  *_ = mock_gen.mock_task(mocker, "subtask", post=[pl.Path("blah.other")])
        subtask2, *_ = mock_gen.mock_task(mocker, "subtask2", post=[pl.Path("test.file")])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)

        next_task = tracker.next_for("task1")
        assert(isinstance(next_task, doot.structs.DootTaskArtifact))

    def test_task_artifact_partial_exists(self, mocker):

        def temp_exists(self):
            return not "*" in self.stem

        mocker.patch.object(pl.Path, "exists", new=temp_exists)

        task1,    *_ = mock_gen.mock_task(mocker, "task1", pre=[pl.Path("*.file")])
        subtask,  *_ = mock_gen.mock_task(mocker, "subtask", post=[pl.Path("blah.other")])
        subtask2, *_ = mock_gen.mock_task(mocker, "subtask2", post=[pl.Path("test.file")])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)

        next_task = tracker.next_for("task1")
        assert(isinstance(next_task, doot.structs.DootTaskArtifact))
