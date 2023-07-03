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
from unittest import mock
##-- end imports
logging = logmod.root


import pytest
from doot.control.tracker import DootTracker
from doot._abstract.task import Task_i

def make_mock_task(name, pre=None, post=None):
    mock_task              = mock.MagicMock(spec=Task_i)
    mock_task.name         = name
    priors                 = pre or mock.PropertyMock()
    posts                  = post or mock.PropertyMock()
    type(mock_task).priors = priors
    type(mock_task).posts  = posts
    return mock_task, priors, posts

class TestTracker:

    def test_initial(self):
        tracker = DootTracker()
        assert(tracker is not None)

    def test_add_task(self):
        mock_task, priors, posts = make_mock_task("test_task")

        tracker = DootTracker()
        tracker.add_task(mock_task)

        assert("test_task" in tracker.tasks)
        assert(tracker.dep_graph.nodes['test_task']['state'] == tracker.state_e.DEFINED)
        priors.assert_called()
        posts.assert_called()

    def test_duplicate_add_fail(self):
        task1, pre1, post1 = make_mock_task("task1")
        task2, pre2, post2 = make_mock_task("task1")

        tracker = DootTracker()
        tracker.add_task(task1)
        with pytest.raises(KeyError):
            tracker.add_task(task2)

        assert("task1" in tracker.tasks)
        pre1.assert_called()
        pre1.assert_called()
        pre2.assert_not_called()
        post2.assert_not_called()

    def test_duplicate_add(self):
        task1, pre1, post1 = make_mock_task("task1")
        task2, pre2, post2 = make_mock_task("task1")

        tracker = DootTracker(shadowing=True)
        tracker.add_task(task1)
        tracker.add_task(task2)

        assert("task1" in tracker.tasks)
        pre1.assert_called()
        pre1.assert_called()
        pre2.assert_called()
        post2.assert_called()

    def test_contains_defined(self):
        mock_task, _, _= make_mock_task("test_task")
        mock_task.priors = ["example", "blah"]

        tracker = DootTracker()
        tracker.add_task(mock_task)
        # defined Task is contained
        assert("test_task" in tracker)

    def test_fail_fast(self):
        task1,    *_ = make_mock_task("task1", pre=["subtask", "subtask2"])
        tracker = DootTracker(fail_fast=True)
        tracker.add_task(task1)

        with pytest.raises(RuntimeError):
            tracker.next_for("task1")

    def test_not_contains_declared(self):
        mock_task, _, _= make_mock_task("test_task", pre=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)
        assert("example" not in tracker)
        assert("blah" not in tracker)

    def test_task_prior_registration(self):
        mock_task, pre, post = make_mock_task("test_task", pre=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)
        assert(tracker.dep_graph.nodes['example']['state'] == tracker.state_e.DECLARED)
        assert(tracker.dep_graph.nodes['blah']['state'] == tracker.state_e.DECLARED)
        assert("example" in tracker.dep_graph)
        assert("blah" in tracker.dep_graph)

    def test_task_post_registration(self):
        mock_task, *_ = make_mock_task("test_task", post=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)
        assert(tracker.dep_graph.nodes['example']['state'] == tracker.state_e.DECLARED)
        assert(tracker.dep_graph.nodes['blah']['state'] == tracker.state_e.DECLARED)
        assert("example" in tracker.dep_graph)
        assert("blah" in tracker.dep_graph)

    def test_declared_set(self):
        mock_task, *_ = make_mock_task("test_task", pre=["subtask", "sub2"], post=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)
        declared = tracker.declared_set()
        assert(declared == {"__root", "test_task", "subtask","sub2", "example", "blah"})

    def test_defined_set(self):
        mock_task, *_ = make_mock_task("test_task", pre=["subtask", "sub2"], post=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)

        defined = tracker.defined_set()
        assert(defined == {"test_task"})

    def test_task_order(self):
        task1,    *_ = make_mock_task("task1", pre=["subtask", "subtask2"])
        subtask,  *_ = make_mock_task("subtask", pre=["subsub"])
        subtask2, *_ = make_mock_task("subtask2", pre=["subsub"])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)

        next_task = tracker.next_for("task1")
        assert(next_task.name in {"subtask", "subtask2"})
        tracker.update_task_state(next_task, tracker.state_e.SUCCESS)
        next_task_2 = tracker.next_for()
        assert(next_task_2.name in {"subtask", "subtask2"} - {next_task.name})
        tracker.update_task_state(next_task_2, tracker.state_e.SUCCESS)
        next_task_3 = tracker.next_for()
        assert(next_task_3.name in "task1")

    def test_task_iter(self):
        task1,    *_ = make_mock_task("task1", pre=["subtask", "subtask2", "subtask3"])
        subtask,  *_ = make_mock_task("subtask", pre=["subsub"])
        subtask2, *_ = make_mock_task("subtask2", pre=["subsub"])
        subtask3, *_ = make_mock_task("subtask3", pre=["subsub"])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)
        tracker.add_task(subtask3)

        tasks = []
        tracker.set_task("task1")
        for x in tracker:
            if x:
                tasks.append(x.name)
                tracker.update_task_state(x.name, tracker.state_e.SUCCESS)

        assert(len(tasks) == 4)

    def test_task_iter_state_changed(self):
        task1,    *_ = make_mock_task("task1", pre=["subtask", "subtask2", "subtask3"])
        subtask,  *_ = make_mock_task("subtask", pre=["subsub"])
        subtask2, *_ = make_mock_task("subtask2", pre=["subsub"])
        subtask3, *_ = make_mock_task("subtask3", pre=["subsub"])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)
        tracker.add_task(subtask3)

        tracker.update_task_state("subtask2", tracker.state_e.SUCCESS)
        tasks = []
        tracker.set_task("task1")
        for x in tracker:
            if x:
                tasks.append(x.name)
                tracker.update_task_state(x.name, tracker.state_e.SUCCESS)

        assert("subtask2" not in tasks)
        assert(len(tasks) == 3)

    def test_task_failure(self):
        task1,    *_ = make_mock_task("task1", pre=["subtask"])
        subtask,  *_ = make_mock_task("subtask", pre=["subsub"])
        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        next_task = tracker.next_for("task1")
        assert(next_task == subtask)
        tracker.update_task_state(subtask, tracker.state_e.FAILURE)

        next_task = tracker.next_for("task1")
        assert(next_task is None)

    def test_post_task_order(self):
        task1,    *_  = make_mock_task("task1", pre=["subtask", "subtask2"])
        subtask,  *_  = make_mock_task("subtask", pre=["subsub"], post=["sidesuper"])
        sidesuper, *_ = make_mock_task("sidesuper")

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(sidesuper)

        next_task = tracker.next_for("task1")
        assert(next_task.name == "subtask")
        tracker.update_task_state(next_task, tracker.state_e.SUCCESS)
        next_task_2 = tracker.next_for()
        assert(next_task_2.name == "task1")
        tracker.update_task_state(next_task_2, tracker.state_e.SUCCESS)
        next_task_3 = tracker.next_for()
        assert(next_task_3 is None)

    def test_task_exact_artifact_dependency(self):
        task1,    *_ = make_mock_task("task1", pre=[pl.Path("test.file")])
        subtask,  *_ = make_mock_task("subtask", post=[pl.Path("blah.other")])
        subtask2, *_ = make_mock_task("subtask2", post=[pl.Path("test.file")])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)
        next_task = tracker.next_for("task1")
        assert(next_task.name == "subtask2")

    def test_task_inexact_artifact_dependency(self):
        task1,    *_ = make_mock_task("task1", pre=[pl.Path("*.file")])
        subtask,  *_ = make_mock_task("subtask", post=[pl.Path("blah.other")])
        subtask2, *_ = make_mock_task("subtask2", post=[pl.Path("test.file")])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)
        next_task = tracker.next_for("task1")
        assert(next_task.name == "subtask2")

    @mock.patch.object(pl.Path, "exists", return_value=True)
    def test_task_artifact_exists(self, mockmeth):
        task1,    *_ = make_mock_task("task1", pre=[pl.Path("*.file")])
        subtask,  *_ = make_mock_task("subtask", post=[pl.Path("blah.other")])
        subtask2, *_ = make_mock_task("subtask2", post=[pl.Path("test.file")])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)

        next_task = tracker.next_for("task1")
        assert(next_task == task1)

    @mock.patch.object(pl.Path, "exists", return_value=False)
    def test_task_artifact_doesnt_exists(self, mockmeth):
        task1,    *_ = make_mock_task("task1", pre=[pl.Path("*.file")])
        subtask,  *_ = make_mock_task("subtask", post=[pl.Path("blah.other")])
        subtask2, *_ = make_mock_task("subtask2", post=[pl.Path("test.file")])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)

        next_task = tracker.next_for("task1")
        assert(next_task == subtask2)

    def test_task_artifact_partial_exists(self):

        def temp_exists(self):
            return not "*" in self.stem

        with mock.patch.object(pl.Path, "exists", new=temp_exists):
            task1,    *_ = make_mock_task("task1", pre=[pl.Path("*.file")])
            subtask,  *_ = make_mock_task("subtask", post=[pl.Path("blah.other")])
            subtask2, *_ = make_mock_task("subtask2", post=[pl.Path("test.file")])

            tracker = DootTracker()
            tracker.add_task(task1)
            tracker.add_task(subtask)
            tracker.add_task(subtask2)

            next_task = tracker.next_for("task1")
            assert(next_task == task1)
