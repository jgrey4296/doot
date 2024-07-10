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
import tomlguard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot

# ##-- end 1st party imports

doot._test_setup()

# ##-- 1st party imports
from doot._abstract import (Action_p, Job_i, Reporter_p, ReportLine_p, Task_i,
                            TaskRunner_i, TaskTracker_i)
from doot.control.runner import DootRunner
from doot.control.tracker import DootTracker
from doot.enums import TaskStatus_e
from doot.structs import ActionSpec, TaskSpec, DKey

# ##-- end 1st party imports

logging = logmod.root



@pytest.mark.parametrize("ctor", [DootRunner])
class TestRunner:

    @pytest.fixture(scope="function")
    def setup(self, mocker):
        min_sleep   = 0.0
        config_dict = {"settings": {"tasks": {"sleep": {"task" : min_sleep, "subtask" : min_sleep, "batch": min_sleep}}}}
        doot.config = tomlguard.TomlGuard(config_dict)

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass


    @pytest.fixture(scope="function")
    def runner(self, ctor, mocker, tracker_mock, reporter_mock):
        runner = ctor(tracker=tracker_mock, reporter=reporter_mock)
        return runner

    @pytest.fixture(scope="function")
    def tracker_mock(self, mocker):
        tracker = mocker.MagicMock(spec=TaskTracker_i)
        tracker.clear_queue = mocker.Mock(return_value=None)
        tracker._tasks = []
        tracker._popped_tasks = []
        def simple_pop():
            if bool(tracker._tasks):
                tracker._popped_tasks.append(tracker._tasks.pop())
                return tracker._popped_tasks[-1]

            return None

        tracker.next_for = simple_pop
        setattr(type(tracker), "__bool__", lambda _: bool(tracker._tasks))

        return tracker

    @pytest.fixture(scope="function")
    def reporter_mock(self, mocker):
        reporter = mocker.MagicMock(spec=Reporter_p)
        return reporter


    @pytest.fixture(scope="function")
    def task_mock(self, mocker):
        return self.make_task_mock(mocker, "agroup::atask")

    def make_task_mock(self, mocker, name):
        task                    = mocker.MagicMock(spec=Task_i, state={})
        task.name = name
        task.spec               = TaskSpec.build({"name": name})
        task.spec.sleep = 0.0
        task.spec.actions = [
            ActionSpec.build({"do":None, "fun": lambda *xs: None})
            ]
        return task

    def make_job_mock(self, mocker, name):
        task                    = mocker.MagicMock(spec=Job_i, state={})
        task.name = name
        task.spec               = TaskSpec.build({"name": name})
        task.spec.sleep = 0.1
        return task


    def test_initial(self, ctor, mocker, setup):
        ## setup
        tracker_m  = mocker.MagicMock(spec=TaskTracker_i)
        reporter_m = mocker.MagicMock(spec=ReportLine_p)
        runner     = ctor(tracker=tracker_m, reporter=reporter_m)

        # Check:
        assert(isinstance(runner, TaskRunner_i))

    def test_tasks_execute(self, ctor, mocker, setup, runner):
        runner._execute_action = lambda *xs: None
        tracker_mock = runner.tracker

        tracker_mock._tasks += [
            self.make_task_mock(mocker, "agroup::first"),
            self.make_task_mock(mocker, "agroup::second"),
            self.make_task_mock(mocker, "agroup::third"),
            ]

        names = [x.name for x in tracker_mock._tasks]

        expand_job                       = mocker.spy(runner, "_expand_job")
        execute_task                     = mocker.spy(runner, "_execute_task")
        execute_action                   = mocker.spy(runner, "_execute_action")

        tracker_mock.set_status.assert_not_called()

        # Run
        runner(handler=False)

        ## check result
        tracker_mock.set_status.assert_called()
        assert(tracker_mock.set_status.call_count == 3)
        for call in tracker_mock.set_status.call_args_list:
            assert(call.args[0].name in names)
            assert(call.args[1] is TaskStatus_e.SUCCESS)

        expand_job.assert_not_called()
        assert(execute_action.call_count == 3)

        execute_task.assert_called()
        assert(execute_task.call_count == 3)
        for call in execute_task.call_args_list:
            assert(str(call.args[0].name) in names)

    def test_jobs_expand(self, ctor, mocker, setup, runner):
        tracker_mock = runner.tracker
        tracker_mock._tasks = [
            self.make_job_mock(mocker, "agroup::first"),
            self.make_job_mock(mocker, "agroup::second"),
            self.make_job_mock(mocker, "agroup::third"),
        ]

        expand_job                                    = mocker.spy(runner, "_expand_job")
        execute_task                                  = mocker.spy(runner, "_execute_task")
        execute_action                                = mocker.spy(runner, "_execute_action")

        ## pre-check
        tracker_mock.set_status.assert_not_called()

        # Run
        runner(handler=False)

        ## check
        tracker_mock.set_status.assert_called()
        assert(tracker_mock.set_status.call_count == 3)

        expand_job.assert_called()
        assert(expand_job.call_count == 3)

        execute_task.assert_not_called()

    def test_tasks_execute_actions(self, ctor, mocker, setup, runner):
        tracker_mock = runner.tracker

        tracker_mock._tasks += [
            self.make_task_mock(mocker, "agroup::first"),
            self.make_task_mock(mocker, "agroup::second"),
            self.make_task_mock(mocker, "agroup::third"),
            ]

        names          = [x.name for x in tracker_mock._tasks]

        expand_job     = mocker.spy(runner, "_expand_job")
        execute_task   = mocker.spy(runner, "_execute_task")
        execute_action = mocker.spy(runner, "_execute_action")

        runner(handler=False)

        tracker_mock.queue_entry.assert_not_called()
        expand_job.assert_not_called()

        tracker_mock.set_status.assert_called()
        assert(tracker_mock.set_status.call_count == 3)

        execute_task.assert_called()
        execute_action.assert_called()
