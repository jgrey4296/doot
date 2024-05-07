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
from doot.structs import DootActionSpec, DootTaskSpec
from doot.utils import mock_gen

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

    def test_initial(self, ctor, mocker, setup):
        ## setup
        tracker_m  = mocker.MagicMock(spec=TaskTracker_i)
        reporter_m = mocker.MagicMock(spec=ReportLine_p)
        runner     = ctor(tracker=tracker_m, reporter=reporter_m)

        # Check:
        assert(isinstance(runner, TaskRunner_i))

    def test_tasks_execute(self, ctor, mocker, setup):
        ## setup
        reporter_m                       = mocker.MagicMock(spec=Reporter_p)

        task1_m                          = mock_gen.mock_task(name="first", actions=0)
        task2_m                          = mock_gen.mock_task(name="second", actions=0)
        task3_m                          = mock_gen.mock_task(name="third", actions=0)

        tracker_m                        = mock_gen.mock_tracker(tasks=[task1_m, task2_m, task3_m])

        runner                           = ctor(tracker=tracker_m, reporter=reporter_m)
        expand_job                       = mocker.spy(runner, "_expand_job")
        execute_task                     = mocker.spy(runner, "_execute_task")
        execute_action                   = mocker.spy(runner, "_execute_action")

        ## pre-check
        tracker_m.set_status.assert_not_called()

        # Run
        runner(handler=False)

        ## check result
        tracker_m.set_status.assert_called()
        assert(tracker_m.set_status.call_count == 3)
        for call in tracker_m.set_status.call_args_list:
            assert(call.args[0].name in ["default::first", "default::second", "default::third"])
            assert(call.args[1] is TaskStatus_e.SUCCESS)

        expand_job.assert_not_called()
        execute_action.assert_not_called()

        execute_task.assert_called()
        assert(execute_task.call_count == 3)
        for call in execute_task.call_args_list:
            assert(str(call.args[0].name) in ["default::first", "default::second", "default::third"])

    def test_jobs_expand(self, ctor, mocker, setup):
        ## setup
        reporter_m                                    = mocker.MagicMock(spec=Reporter_p)

        job1_m                                        = mock_gen.mock_job("first")
        job2_m                                        = mock_gen.mock_job("second")
        job3_m                                        = mock_gen.mock_job("third")

        tracker_m                                     = mock_gen.mock_tracker(tasks=[job1_m, job2_m, job3_m])
        runner                                        = ctor(tracker=tracker_m, reporter=reporter_m)

        expand_job                                    = mocker.spy(runner, "_expand_job")
        execute_task                                  = mocker.spy(runner, "_execute_task")
        execute_action                                = mocker.spy(runner, "_execute_action")

        ## pre-check
        tracker_m.set_status.assert_not_called()

        # Run
        runner(handler=False)

        ## check
        tracker_m.set_status.assert_called()
        assert(tracker_m.set_status.call_count == 3)

        expand_job.assert_called()
        assert(expand_job.call_count == 3)

        execute_task.assert_not_called()

    @pytest.mark.xfail
    def test_tasks_execute_actions(self, ctor, mocker, setup):
        ## setup
        reporter_m                                 = mocker.MagicMock(spec=Reporter_p)

        task1_m = mock_gen.mock_task("firstTask")
        task2_m = mock_gen.mock_task("secondTask")
        task3_m = mock_gen.mock_task("thirdTask")

        tracker_m                        = mock_gen.mock_tracker(tasks=[task1_m, task2_m, task3_m])

        runner                                     = ctor(tracker=tracker_m, reporter=reporter_m)

        expand_job                              = mocker.spy(runner, "_expand_job")
        execute_task                               = mocker.spy(runner, "_execute_task")
        execute_action                             = mocker.spy(runner, "_execute_action")

        ## Run:
        runner(handler=False)

        ## Check
        tracker_m.add_task.assert_not_called()
        expand_job.assert_not_called()

        tracker_m.set_status.assert_called()
        assert(tracker_m.set_status.call_count == 3)

        execute_task.assert_called()
        execute_action.assert_called()
        # TODO action_spec_m.__call__.assert_called()
