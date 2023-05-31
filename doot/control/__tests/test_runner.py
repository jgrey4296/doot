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

##-- warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    pass
##-- end warnings

from doot.control.runner import DootTracker, DootRunner
from doot._abstract.task import DootTask_i

def make_mock_task(name, pre=None, post=None):
    mock_task              = mock.MagicMock(spec=DootTask_i)
    mock_task.name         = name
    priors                 = pre or mock.PropertyMock()
    posts                  = post or mock.PropertyMock()
    type(mock_task).priors = priors
    type(mock_task).posts  = posts
    return mock_task, priors, posts

class TestTracker(unittest.TestCase):
    ##-- setup-teardown
    @classmethod
    def setUpClass(cls):
        LOGLEVEL      = logmod.DEBUG
        LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)

        cls.file_h        = logmod.FileHandler(LOG_FILE_NAME, mode="w")
        cls.file_h.setLevel(LOGLEVEL)

        logging.setLevel(logmod.NOTSET)
        logging.addHandler(cls.file_h)


    @classmethod
    def tearDownClass(cls):
        logging.removeHandler(cls.file_h)

    ##-- end setup-teardown

    def test_initial(self):
        tracker = DootTracker()
        self.assertTrue(tracker)

    def test_add_task(self):
        mock_task, priors, posts = make_mock_task("test_task")

        tracker = DootTracker()
        tracker.add_task(mock_task)

        self.assertTrue("test_task" in tracker.tasks)
        self.assertEqual(tracker.dep_graph.nodes['test_task']['state'], tracker.state_e.DEFINED)
        priors.assert_called()
        posts.assert_called()

    def test_duplicate_add(self):
        task1, pre1, post1 = make_mock_task("task1")
        task2, pre2, post2 = make_mock_task("task1")

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(task2)

        self.assertTrue("task1" in tracker.tasks)
        pre1.assert_called()
        pre1.assert_called()
        pre2.assert_not_called()
        post2.assert_not_called()

    def test_contains_defined(self):
        mock_task, _, _= make_mock_task("test_task")
        mock_task.priors = ["example", "blah"]

        tracker = DootTracker()
        tracker.add_task(mock_task)
        # defined Task is contained
        self.assertIn("test_task", tracker)

    def test_not_contains_declared(self):
        mock_task, _, _= make_mock_task("test_task", pre=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)
        self.assertNotIn("example", tracker)
        self.assertNotIn("blah", tracker)

    def test_task_prior_registration(self):
        mock_task, pre, post = make_mock_task("test_task", pre=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)
        self.assertEqual(tracker.dep_graph.nodes['example']['state'], tracker.state_e.DECLARED)
        self.assertEqual(tracker.dep_graph.nodes['blah']['state'], tracker.state_e.DECLARED)
        self.assertIn("example", tracker.dep_graph)
        self.assertIn("blah", tracker.dep_graph)

    def test_task_post_registration(self):
        mock_task, *_ = make_mock_task("test_task", post=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)
        self.assertEqual(tracker.dep_graph.nodes['example']['state'], tracker.state_e.DECLARED)
        self.assertEqual(tracker.dep_graph.nodes['blah']['state'], tracker.state_e.DECLARED)
        self.assertIn("example", tracker.dep_graph)
        self.assertIn("blah", tracker.dep_graph)

    def test_declared_set(self):
        mock_task, *_ = make_mock_task("test_task", pre=["subtask", "sub2"], post=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)
        declared = tracker.declared_set()
        self.assertEqual(declared, {"test_task", "subtask","sub2", "example", "blah"})

    def test_defined_set(self):
        mock_task, *_ = make_mock_task("test_task", pre=["subtask", "sub2"], post=["example", "blah"])

        tracker = DootTracker()
        tracker.add_task(mock_task)
        declared = tracker.defined_set()
        self.assertEqual(declared, {"test_task"})

    def test_task_order(self):
        task1,    *_ = make_mock_task("task1", pre=["subtask", "subtask2"])
        subtask,  *_ = make_mock_task("subtask", pre=["subsub"])
        subtask2, *_ = make_mock_task("subtask2", pre=["subsub"])

        tracker = DootTracker()
        tracker.add_task(task1)
        tracker.add_task(subtask)
        tracker.add_task(subtask2)

        next_task = tracker.next_for("task1")
        self.assertIn(next_task.name, {"subtask", "subtask2"})
        tracker.update_task_state(next_task, tracker.state_e.SUCCESS)
        next_task_2 = tracker.next_for()
        self.assertIn(next_task_2.name, {"subtask", "subtask2"} - {next_task.name})
        tracker.update_task_state(next_task_2, tracker.state_e.SUCCESS)
        next_task_3 = tracker.next_for()
        self.assertEqual(next_task_3.name, "task1")



##-- ifmain
if __name__ == '__main__':
    unittest.main()
##-- end ifmain
