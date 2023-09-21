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

from doot.enums import TaskStateEnum
from doot.control.runner import DootRunner
from doot.control.tracker import DootTracker
from doot.structs import DootTaskSpec
from doot._abstract import Tasker_i, Task_i, TaskTracker_i, TaskRunner_i, ReportLine_i, Action_p, Reporter_i

logging = logmod.root

# caplog
# mocker.patch | patch.object | patch.multiple | patch.dict | stopall | stop | spy | stub
# pytest.mark.filterwarnings
# pytest.parameterize
# pytest.skip | skipif | xfail
# with pytest.deprecated_call
# with pytest.raises
# with pytest.warns(warntype)

class TestRunner:
    def test_initial(self, mocker):
        ##-- setup
        tracker_m  = mocker.MagicMock(spec=TaskTracker_i)
        reporter_m = mocker.MagicMock(spec=ReportLine_i)
        runner     = DootRunner(tracker=tracker_m, reporter=reporter_m)
        ##-- end setup

        # Check:
        assert(isinstance(runner, TaskRunner_i))

    def test_tasks_execute(self, mocker):
        ##-- setup
        tracker_m                       = mocker.MagicMock(spec=TaskTracker_i)
        reporter_m                      = mocker.MagicMock(spec=Reporter_i)
        runner                          = DootRunner(tracker=tracker_m, reporter=reporter_m)

        task1_m                          = mocker.MagicMock(spec=Task_i)
        task1_m.name                     = "first"
        task1_m.spec                     = mocker.MagicMock(spec=DootTaskSpec)
        task1_m.spec.print_level         = "WARN"
        task2_m                          = mocker.MagicMock(spec=Task_i)
        task2_m.name                     = "second"
        task2_m.spec                     = mocker.MagicMock(spec=DootTaskSpec)
        task2_m.spec.print_level         = "WARN"
        task3_m                          = mocker.MagicMock(spec=Task_i)
        task3_m.name                     = "third"
        task3_m.spec                     = mocker.MagicMock(spec=DootTaskSpec)
        task3_m.spec.print_level         = "WARN"

        tracker_m.__iter__.return_value  = [task1_m, task2_m, task3_m]

        expand_tasker  = mocker.spy(runner, "_expand_tasker")
        execute_task   = mocker.spy(runner, "_execute_task")
        execute_action = mocker.spy(runner, "_execute_action")
        ##-- end setup

        ##-- pre-check
        tracker_m.update_state.assert_not_called()
        ##-- end pre-check

        # Run
        runner()

        ##-- check result
        tracker_m.update_state.assert_called()
        assert(tracker_m.update_state.call_count == 3)
        for call in tracker_m.update_state.call_args_list:
            assert(call.args[0].name in ["first", "second", "third"])
            assert(call.args[1] is TaskStateEnum.SUCCESS)

        expand_tasker.assert_not_called()
        execute_action.assert_not_called()

        execute_task.assert_called()
        assert(execute_task.call_count == 3)
        for call in execute_task.call_args_list:
            assert(call.args[0].name in ["first", "second", "third"])
        ##-- end check result

    def test_taskers_expand(self, mocker):
        ##-- setup
        tracker_m                            = mocker.MagicMock(spec=TaskTracker_i)
        reporter_m                           = mocker.MagicMock(spec=Reporter_i)
        runner                               = DootRunner(tracker=tracker_m, reporter=reporter_m)

        tasker1_m                            = mocker.MagicMock(spec=Tasker_i)
        tasker1_m.spec                       = mocker.MagicMock(spec=DootTaskSpec)
        tasker1_m.spec.print_level           = "WARN"
        tasker2_m                            = mocker.MagicMock(spec=Tasker_i)
        tasker2_m.spec                       = mocker.MagicMock(spec=DootTaskSpec)
        tasker2_m.spec.print_level           = "WARN"
        tasker3_m                            = mocker.MagicMock(spec=Tasker_i)
        tasker3_m.spec                       = mocker.MagicMock(spec=DootTaskSpec)
        tasker3_m.spec.print_level           = "WARN"

        tracker_m.__iter__.return_value      = [tasker1_m, tasker2_m, tasker3_m]

        expand_tasker                        = mocker.spy(runner, "_expand_tasker")
        execute_task                         = mocker.spy(runner, "_execute_task")
        execute_action                       = mocker.spy(runner, "_execute_action")
        ##-- end setup

        ##-- pre-check
        tracker_m.update_state.assert_not_called()
        ##-- end pre-check

        # Run
        runner()

        ##-- check
        tracker_m.update_state.assert_called()
        assert(tracker_m.update_state.call_count == 3)

        expand_tasker.assert_called()
        assert(expand_tasker.call_count == 3)

        execute_action.assert_not_called()
        execute_task.assert_not_called()
        ##-- end check

    def test_taskers_add_tasks(self, mocker):
        ##-- setup
        tracker_m                          = mocker.MagicMock(spec=TaskTracker_i)
        reporter_m                         = mocker.MagicMock(spec=Reporter_i)
        runner                             = DootRunner(tracker=tracker_m, reporter=reporter_m)

        spec_m                             = mocker.MagicMock(spec=DootTaskSpec)
        spec_m.print_level                 = "WARN"

        tasker1_m                          = mocker.MagicMock(spec=Tasker_i)
        tasker1_m.spec                     = spec_m
        tasker2_m                          = mocker.MagicMock(spec=Tasker_i)
        tasker2_m.spec                     = spec_m
        tasker3_m                          = mocker.MagicMock(spec=Tasker_i)
        tasker3_m.spec                     = spec_m

        task_m      = mocker.MagicMock(spec=Task_i)

        tasker1_m.build.return_value = [task_m]
        tracker_m.__iter__.return_value = [tasker1_m, tasker2_m, tasker3_m]

        expand_tasker  = mocker.spy(runner, "_expand_tasker")
        execute_task   = mocker.spy(runner, "_execute_task")
        execute_action = mocker.spy(runner, "_execute_action")
        ##-- end setup

        ##-- pre-check
        tracker_m.update_state.assert_not_called()
        ##-- end pre-check

        ## Run:
        runner()

        ##-- Check
        tracker_m.add_task.assert_called()
        assert(tracker_m.add_task.call_count == 1)
        assert(tracker_m.add_task.call_args.args[0] is task_m)

        tracker_m.update_state.assert_called()
        assert(tracker_m.update_state.call_count == 3)

        expand_tasker.assert_called()
        assert(expand_tasker.call_count == 3)

        execute_action.assert_not_called()
        execute_task.assert_not_called()

    def test_tasks_execute_actions(self, mocker):
        ##-- setup
        tracker_m                       = mocker.MagicMock(spec=TaskTracker_i)
        reporter_m                      = mocker.MagicMock(spec=Reporter_i)
        runner                          = DootRunner(tracker=tracker_m, reporter=reporter_m)
        spec_m                          = mocker.MagicMock(spec=DootTaskSpec)
        spec_m.print_level              = "WARN"

        action_m                        = mocker.MagicMock(spec=Action_p)
        action_m.spec                   = "blah"
        task1_m                         = mocker.MagicMock(spec=Task_i)
        task1_m.name                    = "firstTask"
        task1_m.spec                    = spec_m
        task1_m.state                   = {}
        type(task1_m).actions           = mocker.PropertyMock(return_value=[action_m])
        task2_m                         = mocker.MagicMock(spec=Task_i)
        task2_m.name                    = "secondTask"
        task2_m.spec                    = spec_m
        task3_m                         = mocker.MagicMock(spec=Task_i)
        task3_m.name                    = "thirdTask"
        task3_m.spec                    = spec_m

        tracker_m.__iter__.return_value = [task1_m, task2_m, task3_m]

        expand_tasker  = mocker.spy(runner, "_expand_tasker")
        execute_task   = mocker.spy(runner, "_execute_task")
        execute_action = mocker.spy(runner, "_execute_action")
        ##-- end setup

        ##-- pre-check
        ##-- end pre-check

        ## Run:
        runner()

        ##-- Check
        tracker_m.add_task.assert_not_called()
        expand_tasker.assert_not_called()

        tracker_m.update_state.assert_called()
        assert(tracker_m.update_state.call_count == 3)

        execute_task.assert_called()
        execute_action.assert_called()
        action_m.assert_called()
