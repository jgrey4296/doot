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
from types import MethodType
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
from jgdv.structs.chainguard import ChainGuard
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot

# ##-- end 1st party imports

doot._test_setup()

# ##-- 1st party imports
from doot._abstract import (Action_p, Job_i, Reporter_p, ReportLine_p, Task_i, TaskRunner_i, TaskTracker_i)
from doot.control.runner import DootRunner
from doot.control.naive_tracker import DootTracker
from doot.enums import TaskStatus_e
from doot.structs import ActionSpec, TaskSpec, DKey, TaskName
from doot.control.naive_tracker import DootTracker
from doot.reporters.base_reporter import BaseReporter
from doot.task import DootTask, DootJob

# ##-- end 1st party imports

logging = logmod.root

class _MockObjs_m:

    @pytest.fixture(scope="function")
    def setup_config(self, mocker):
        """ Setup config values so theres no sleep wait """
        min_sleep   = 0.0
        config_dict = {"settings": {"tasks": {"sleep": {"task" : min_sleep, "subtask" : min_sleep, "batch": min_sleep}}}}
        doot.config = ChainGuard(config_dict)

    @pytest.fixture(scope="function")
    def runner(self, ctor, mocker):
        tracker  = DootTracker()
        reporter = BaseReporter()
        runner   = ctor(tracker=tracker, reporter=reporter)
        return runner

@pytest.mark.parametrize("ctor", [DootRunner])
class TestRunner(_MockObjs_m):

    def test_sanity(self, ctor):
        assert(True is not False) # noqa: PLR0133

    def test_initial(self, ctor, mocker, setup_config, runner):
        # Check:
        assert(isinstance(runner, TaskRunner_i))

    def test_expand_job(self, ctor, mocker, setup_config, runner):
        announce_entry_spy    = mocker.spy(runner, "_announce_entry")
        test_cond_spy         = mocker.spy(runner, "_test_conditions")
        add_trace_spy         = mocker.spy(runner.reporter, "add_trace")
        exec_action_group_spy = mocker.spy(runner, "_execute_action_group")

        spec                  = TaskSpec.build("basic::job")
        job                   = DootJob(spec)
        runner._expand_job(job)

        announce_entry_spy.assert_called_once()
        test_cond_spy.assert_called_once()
        assert(test_cond_spy.spy_return == True)
        add_trace_spy.assert_called()
        exec_action_group_spy.assert_called()

    def test_expand_job_with_a_task_errors(self, ctor, mocker, setup_config, runner):
        spec                  = TaskSpec.build("basic::job")
        task                  = DootTask(spec)
        with pytest.raises(AssertionError):
            runner._expand_job(task)


    def test_expand_job_fails_conditions(self, ctor, mocker, setup_config, runner):
        announce_entry_spy      = mocker.spy(runner, "_announce_entry")
        add_trace_spy           = mocker.spy(runner.reporter, "add_trace")
        exec_action_group_spy   = mocker.spy(runner, "_execute_action_group")

        orig_method = runner._test_conditions

        def override_tests(self, job):
            orig_method(job)
            return False

        runner._test_conditions = MethodType(override_tests, runner)

        spec                  = TaskSpec.build("basic::job")
        job                   = DootJob(spec)
        runner._expand_job(job)
        exec_action_group_spy.assert_called_with(job, group="depends_on")

    def test_execute_task(self, ctor, mocker, setup_config, runner):
        announce_entry_spy    = mocker.spy(runner, "_announce_entry")
        test_cond_spy         = mocker.spy(runner, "_test_conditions")
        add_trace_spy         = mocker.spy(runner.reporter, "add_trace")
        exec_action_group_spy = mocker.spy(runner, "_execute_action_group")

        spec                  = TaskSpec.build("basic::job")
        task                  = DootTask(spec)
        runner._execute_task(task)

        announce_entry_spy.assert_called_once()
        test_cond_spy.assert_called_once()
        assert(test_cond_spy.spy_return == True)
        add_trace_spy.assert_called()
        exec_action_group_spy.assert_called()


    def test_execute_task_with_a_job_errors(self, ctor, mocker, setup_config, runner):
        spec                  = TaskSpec.build("basic::job")
        job                   = DootJob(spec)
        with pytest.raises(AssertionError):
            runner._execute_task(job)


    def test_execute_task_fails_conditions(self, ctor, mocker, setup_config, runner):
        announce_entry_spy      = mocker.spy(runner, "_announce_entry")
        add_trace_spy           = mocker.spy(runner.reporter, "add_trace")
        exec_action_group_spy   = mocker.spy(runner, "_execute_action_group")

        orig_method = runner._test_conditions

        def override_tests(self, job):
            orig_method(job)
            return False

        runner._test_conditions = MethodType(override_tests, runner)

        spec = TaskSpec.build("basic::job")
        task = DootTask(spec)
        runner._execute_task(task)
        exec_action_group_spy.assert_called_with(task, group="depends_on")
