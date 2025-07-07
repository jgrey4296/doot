#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN202, ANN001, ARG002, ARG001, E712
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
from types import MethodType
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.control.runner.runner import DootRunner
from doot.control.tracker import NaiveTracker
from doot.util.dkey import DKey
from doot.util.factory import TaskFactory
from doot.workflow import ActionSpec, DootJob, DootTask, TaskName, TaskSpec
from doot.workflow._interface import TaskStatus_e

# ##-- end 1st party imports

from .. import _interface as API # noqa: N812
from doot.workflow._interface import Action_p
from doot.control.runner._interface import WorkflowRunner_p

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
# isort: on
# ##-- end types

logging = logmod.root
logmod.getLogger("jgdv").propagate = False
factory = TaskFactory()

class _MockObjs_m:

    @pytest.fixture(scope="function")
    def setup_config(self, mocker):
        """ Setup config values so theres no sleep wait """
        min_sleep   = 0.0
        config_dict = {"settings": {"tasks": {"sleep": {"task" : min_sleep, "subtask" : min_sleep, "batch": min_sleep}}}}
        doot.config = ChainGuard(config_dict)

    @pytest.fixture(scope="function")
    def runner(self, ctor, mocker):
        tracker  = NaiveTracker()
        runner   = ctor(tracker=tracker)
        return runner

@pytest.mark.parametrize("ctor", [DootRunner])
class TestRunner(_MockObjs_m):

    def test_sanity(self, ctor):
        assert(True is not False) # noqa: PLR0133

    def test_initial(self, ctor):
        # Check:
        assert(isinstance(ctor, API.WorkflowRunner_p))
        assert(isinstance(ctor, API.RunnerHandlers_p))

@pytest.mark.parametrize("ctor", [DootRunner])
class TestRunner_Jobs(_MockObjs_m):

    def test_sanity(self, ctor):
        assert(True is not False) # noqa: PLR0133

    def test_expand_job(self, ctor, mocker, setup_config, runner):
        test_cond_spy         = mocker.spy(runner.executor, "test_conditions")
        exec_action_group_spy = mocker.spy(runner.executor, "execute_action_group")

        spec                  = factory.build("basic::job")
        job                   = DootJob(spec)
        runner.expand_job(job)

        test_cond_spy.assert_called_once()
        assert(test_cond_spy.spy_return == True)
        exec_action_group_spy.assert_called()

    def test_expand_job_with_a_task_errors(self, ctor, mocker, setup_config, runner):
        spec = factory.build("basic::job")
        task = DootTask(spec)
        with pytest.raises(AssertionError):
            runner.expand_job(task)

    def test_expand_job_fails_conditions(self, ctor, mocker, setup_config, runner):
        exec_action_group_spy  = mocker.spy(runner.executor, "execute_action_group")
        orig_method            = runner.executor.test_conditions

        def override_tests(self, job, *, large_step:int):
            orig_method(job, large_step=large_step)
            return False

        runner.executor.test_conditions = MethodType(override_tests, runner)

        spec                  = factory.build("basic::job")
        job                   = DootJob(spec)
        runner.expand_job(job)
        exec_action_group_spy.assert_called()
        exec_action_group_spy.assert_called_with(job, group="depends_on", large_step=0)

@pytest.mark.parametrize("ctor", [DootRunner])
class TestRunner_Tasks(_MockObjs_m):

    def test_sanity(self, ctor):
        assert(True is not False) # noqa: PLR0133

    def test_execute_task(self, ctor, mocker, setup_config, runner):
        test_cond_spy         = mocker.spy(runner.executor, "test_conditions")
        exec_action_group_spy = mocker.spy(runner.executor, "execute_action_group")

        spec                  = factory.build("basic::job")
        task                  = DootTask(spec)
        runner.execute_task(task)

        test_cond_spy.assert_called_once()
        assert(test_cond_spy.spy_return == True)
        exec_action_group_spy.assert_called()

    def test_execute_task_with_a_job_errors(self, ctor, mocker, setup_config, runner):
        spec                  = factory.build("basic::job")
        job                   = DootJob(spec)
        with pytest.raises(AssertionError):
            runner.execute_task(job)

    def test_execute_task_fails_conditions(self, ctor, mocker, setup_config, runner):
        exec_action_group_spy   = mocker.spy(runner.executor, "execute_action_group")

        orig_method = runner.executor.test_conditions

        def override_tests(self, job, **kwargs:Any):
            orig_method(job, **kwargs)
            return False

        runner.executor.test_conditions = MethodType(override_tests, runner)

        spec = factory.build("basic::job")
        task = DootTask(spec)
        runner.execute_task(task)
        exec_action_group_spy.assert_called_with(task, group="depends_on", large_step=0)
