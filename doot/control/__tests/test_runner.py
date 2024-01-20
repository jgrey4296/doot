#!/usr/bin/env python3
"""

"""
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings

import pytest

import tomlguard
import doot
from doot.enums import TaskStateEnum
from doot.control.runner import DootRunner
from doot.control.tracker import DootTracker
from doot.structs import DootTaskSpec, DootActionSpec
from doot._abstract import Job_i, Task_i, TaskTracker_i, TaskRunner_i, ReportLine_i, Action_p, Reporter_i
from doot.utils import mock_gen

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

    def test_initial(self, ctor, mocker, setup):
        ##-- setup
        tracker_m  = mocker.MagicMock(spec=TaskTracker_i)
        reporter_m = mocker.MagicMock(spec=ReportLine_i)
        runner     = ctor(tracker=tracker_m, reporter=reporter_m)
        ##-- end setup

        # Check:
        assert(isinstance(runner, TaskRunner_i))

    def test_tasks_execute(self, ctor, mocker, setup):
        ##-- setup
        reporter_m                       = mocker.MagicMock(spec=Reporter_i)

        task1_m                          = mock_gen.mock_task(name="first", actions=0)
        task2_m                          = mock_gen.mock_task(name="second", actions=0)
        task3_m                          = mock_gen.mock_task(name="third", actions=0)

        tracker_m                        = mock_gen.mock_tracker(tasks=[task1_m, task2_m, task3_m])

        runner                           = ctor(tracker=tracker_m, reporter=reporter_m)
        expand_job                       = mocker.spy(runner, "_expand_job")
        execute_task                     = mocker.spy(runner, "_execute_task")
        execute_action                   = mocker.spy(runner, "_execute_action")
        ##-- end setup

        ##-- pre-check
        tracker_m.update_state.assert_not_called()
        ##-- end pre-check

        # Run
        runner(handler=False)

        ##-- check result
        tracker_m.update_state.assert_called()
        assert(tracker_m.update_state.call_count == 3)
        for call in tracker_m.update_state.call_args_list:
            assert(call.args[0].name in ["first", "second", "third"])
            assert(call.args[1] is tracker_m.state_e.SUCCESS)

        expand_job.assert_not_called()
        execute_action.assert_not_called()

        execute_task.assert_called()
        assert(execute_task.call_count == 3)
        for call in execute_task.call_args_list:
            assert(call.args[0].name in ["first", "second", "third"])
        ##-- end check result

    def test_jobs_expand(self, ctor, mocker, setup):
        ##-- setup
        reporter_m                                    = mocker.MagicMock(spec=Reporter_i)

        job1_m                                        = mock_gen.mock_job("first")
        job2_m                                        = mock_gen.mock_job("second")
        job3_m                                        = mock_gen.mock_job("third")

        tracker_m                                     = mock_gen.mock_tracker(tasks=[job1_m, job2_m, job3_m])
        runner                                        = ctor(tracker=tracker_m, reporter=reporter_m)

        expand_job                                    = mocker.spy(runner, "_expand_job")
        execute_task                                  = mocker.spy(runner, "_execute_task")
        execute_action                                = mocker.spy(runner, "_execute_action")
        ##-- end setup

        ##-- pre-check
        tracker_m.update_state.assert_not_called()
        ##-- end pre-check

        # Run
        runner(handler=False)

        ##-- check
        tracker_m.update_state.assert_called()
        assert(tracker_m.update_state.call_count == 3)

        expand_job.assert_called()
        assert(expand_job.call_count == 3)

        execute_action.assert_not_called()
        execute_task.assert_not_called()
        ##-- end check

    def test_jobs_add_tasks(self, ctor, mocker, setup):
        ##-- setup
        reporter_m                         = mocker.MagicMock(spec=Reporter_i)

        job1_m                             = mock_gen.mock_job("first")
        job2_m                             = mock_gen.mock_job("second")
        job3_m                             = mock_gen.mock_job("third")

        task_m                             = mock_gen.mock_task_spec("firstTask")
        job1_m.build.return_value          = [task_m]

        tracker_m                        = mock_gen.mock_tracker(tasks=[job1_m, job2_m, job3_m])
        runner                             = ctor(tracker=tracker_m, reporter=reporter_m)
        expand_job                         = mocker.spy(runner, "_expand_job")
        execute_task                       = mocker.spy(runner, "_execute_task")
        execute_action                     = mocker.spy(runner, "_execute_action")
        ##-- end setup

        ##-- pre-check
        tracker_m.update_state.assert_not_called()
        ##-- end pre-check

        ## Run:
        runner(handler=False)

        ##-- Check
        tracker_m.add_task.assert_called()
        assert(tracker_m.add_task.call_count == 1)
        assert(tracker_m.add_task.call_args.args[0] is task_m)

        tracker_m.update_state.assert_called()
        assert(tracker_m.update_state.call_count == 3)

        expand_job.assert_called()
        assert(expand_job.call_count == 3)

        execute_action.assert_not_called()
        execute_task.assert_not_called()

    # @pytest.mark.xfail
    def test_tasks_execute_actions(self, ctor, mocker, setup):
        ##-- setup
        reporter_m                                 = mocker.MagicMock(spec=Reporter_i)

        task1_m = mock_gen.mock_task("firstTask")
        task2_m = mock_gen.mock_task("secondTask")
        task3_m = mock_gen.mock_task("thirdTask")

        tracker_m                        = mock_gen.mock_tracker(tasks=[task1_m, task2_m, task3_m])

        runner                                     = ctor(tracker=tracker_m, reporter=reporter_m)

        expand_job                              = mocker.spy(runner, "_expand_job")
        execute_task                               = mocker.spy(runner, "_execute_task")
        execute_action                             = mocker.spy(runner, "_execute_action")
        ##-- end setup

        ##-- pre-check
        ##-- end pre-check

        ## Run:
        runner(handler=False)

        ##-- Check
        tracker_m.add_task.assert_not_called()
        expand_job.assert_not_called()

        tracker_m.update_state.assert_called()
        assert(tracker_m.update_state.call_count == 3)

        execute_task.assert_called()
        execute_action.assert_called()
        # TODO action_spec_m.__call__.assert_called()
