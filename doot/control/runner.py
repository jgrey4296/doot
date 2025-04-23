#!/usr/bin/env python3
"""

"""
# ruff: noqa: N812
# mypy: disable-error-code="attr-defined"
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from collections import defaultdict
from contextlib import nullcontext
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto, Mixin
import networkx as nx
from jgdv.debugging import SignalHandler, NullHandler
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._structs.relation_spec import RelationSpec
from doot.enums import ActionResponse_e as ActRE
from doot.structs import ActionSpec, TaskArtifact, TaskName, TaskSpec

from . import _runner_util as RU

# ##-- end 1st party imports

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
from doot._abstract import (Action_p, Job_p, Task_p, TaskRunner_p, TaskTracker_p)
# isort: on
# ##-- end types

##-- logging
logging           = logmod.getLogger(__name__)
##-- end logging

##--| Vars
skip_msg                   : Final[str] = doot.constants.printer.skip_by_condition_msg
max_steps                  : Final[int] = doot.config.on_fail(100_000).settings.tasks.max_steps()

SETUP_GROUP                : Final[str] = "setup"
ACTION_GROUP               : Final[str] = "actions"
FAIL_GROUP                 : Final[str] = "on_fail"
DEPENDS_GROUP              : Final[str] = "depends_on"

##--|

class _ActionExecution_m:
    """ Covers the nuts and bolts of executing an action group """

    def _execute_action_group(self, task:Task_p, *, allow_queue:bool=False, group:Maybe[str]=None) -> Maybe[tuple[int, ActRE]]:
        """ Execute a group of actions, possibly queue any task specs they produced,
        and return a count of the actions run + the result
        """
        actions = task.get_action_group(group)

        if not bool(actions):
            return None

        doot.report.act("ActGroup", group)
        group_result              = ActRE.SUCCESS
        to_queue : list[TaskSpec] = []
        executed_count            = 0

        for action in actions:
            if self._skip_relation_specs(action):
                continue

            match self._execute_action(executed_count, action, task):
                case True | None:
                    continue
                case list() as result:
                    to_queue += result
                case False:
                    group_result = ActRE.FAIL
                    break
                case ActRE.SKIP:
                    doot.report.line("Remaining Task Actions skipped by Action Result", char=".")
                    group_result = ActRE.SKIP
                    break

            executed_count += 1

        else: # no break.
            match self._maybe_queue_more_tasks(to_queue, allowed=allow_queue):
                case None:
                    pass
                case x:
                    group_result = x

        return executed_count, group_result

    def _skip_relation_specs(self, action:RelationSpec|ActionSpec) -> bool:
        """ return of True signals the action is a relationspec, so is to be ignored """
        match action:
            case RelationSpec():
                return True
            case ActionSpec():
                return False
            case _:
                raise doot.errors.TaskError("Task Failed: Bad Action: %s", repr(action))

    def _maybe_queue_more_tasks(self, new_tasks:list, *, allowed:bool=False) -> Maybe[ActRE]:
        """ When 'allowed', an action group can queue more tasks in the tracker,
        can return a new ActRE to describe the result status of this group
        """
        if bool(new_tasks) and not allowed:
            doot.report.error("Tried to Queue additional tasks from a bad action group")
            return ActRE.FAIL

        new_nodes = []
        failures  = []
        for spec in new_tasks:
            match self.tracker.queue_entry(spec):
                case None:
                    failures.append(spec.name)
                case TaskName() as x:
                    new_nodes.append(x)

        if bool(failures):
            doot.report.error("Queuing a generated specs failed: %s", failures)
            return ActRE.FAIL

        if bool(new_nodes):
            self.tracker.build_network(sources=new_nodes)
            doot.report.trace("Queued %s Subtasks", len(new_nodes))

        return None

    def _execute_action(self, count:int, action:Action_p, task:Task_p) -> ActRE|list:
        """ Run the given action of a specific task.

          returns either a list of specs to (potentially) queue,
          or an ActRE describing the action result.

        """
        result                     = None
        task.state['_action_step'] = count
        # doot.report.add_trace(action, flags=Report_f.ACTION | Report_f.INIT)
        doot.report.act(f"Action: {self.step}.{count}", action.do)

        logging.detail("Action Executing for Task: %s", task.shortname)
        logging.detail("Action State: %s.%s: args=%s kwargs=%s. state(size)=%s", self.step, count, action.args, dict(action.kwargs), len(task.state.keys()))
        result = action(task.state)
        match result:
            case None | True:
                result = ActRE.SUCCESS
            case False | ActRE.FAIL:
                doot.report.fail()
                raise doot.errors.TaskFailed("Task %s: Action Failed: %s", task.shortname, action.do, task=task.spec)
            case ActRE.SKIP:
                # result will be returned, and expand_job/execute_task will handle it
                doot.report.result(["Skip"])
                pass
            case dict(): # update the task's state
                task.state.update({str(k):v for k,v in result.items()})
                result = ActRE.SUCCESS
            case list() if all(isinstance(x, TaskName|TaskSpec) for x in result):
                pass
            case _:
                raise doot.errors.TaskError("Task %s: Action %s Failed: Returned an unplanned for value: %s", task.shortname, action.do, result, task=task.spec)

        # doot.report.add_trace(action, flags=Report_f.ACTION | Report_f.SUCCEED)
        return result

##--|

@Proto(TaskRunner_p, check=False)
@Mixin(_ActionExecution_m, RU._RunnerCtx_m, RU._RunnerHandlers_m, RU._RunnerSleep_m)
class DootRunner:
    """ The simplest single threaded task runner """

    step          : int
    tracker       : TaskTracker_p
    teardown_list : list

    def __init__(self:Self, *, tracker:TaskTracker_p):
        super().__init__()
        self.step          = 0
        self.tracker       = tracker
        self.teardown_list = [] # list of tasks to teardown

    def __call__(self, *tasks:str, handler:Maybe[Callable]=None): #noqa: ARG002
        """ tasks are initial targets to run.
          so loop on the tracker, getting the next task,
          running its actions,
          and repeating,
          until done

          if task is a job, it is expanded and added into the tracker
          """
        match handler:
            case True:
                handler = SignalHandler()
            case False:
                handler = NullHandler()
            case type() as x:
                handler = x()
            case x if hasattr(x, "__enter__"):
                handler = x
            case _:
                handler = nullcontext()

        with handler:
            while bool(self.tracker) and self.step < max_steps:
                self._run_next_task()

    def _run_next_task(self) -> None:
        """
          Get the next task from the tracker, expand/run it,
          and handle the result/failure
        """
        task = None
        try:
            match (task:=self.tracker.next_for()):
                case None:
                    pass
                case TaskArtifact():
                    self._notify_artifact(task)
                case Job_p():
                    self._expand_job(task)
                case Task_p():
                    self._execute_task(task)
                case x:
                    doot.report.error("Unknown Value provided to runner: %s", x)
        except doot.errors.TaskError as err:
            # doot.report.add_trace(task.spec, flags=Report_f.FAIL | Report_f.TASK)
            err.task = task
            self._handle_failure(err)
        except doot.errors.DootError as err:
            self._handle_failure(err)
        except Exception as err:
            self.tracker.clear_queue()
            raise
        else:
            self._handle_task_success(task)
            self._sleep(task)
            self.step += 1

    def _expand_job(self, job:Job_p) -> None:
        """ turn a job into all of its tasks, including teardowns """
        logmod.debug("-- Expanding Job %s: %s", self.step, job.shortname)
        assert(isinstance(job, Job_p))
        try:
            doot.report.branch(job.spec.name.root(), info=f"Job {self.step}")
            if not self._test_conditions(job):
                doot.report.trace(skip_msg, self.step, job.name.root())
                return

            self._execute_action_group(job, group=SETUP_GROUP)
            self._execute_action_group(job, allow_queue=True, group=ACTION_GROUP)
        except doot.errors.DootError as err:
            self._execute_action_group(job, group=FAIL_GROUP)
            raise

    def _execute_task(self, task:Task_p) -> None:
        """ execute a single task's actions """
        logmod.debug("-- Expanding Task %s: %s", self.step, task.shortname)
        assert(not isinstance(task, Job_p))
        try:
            doot.report.branch(task.spec.name.root(), info=f"Task {self.step}")
            if not self._test_conditions(task):
                doot.report.result([skip_msg, self.step, task.name.root()])
                return


            self._execute_action_group(task, group=SETUP_GROUP)
            self._execute_action_group(task, group=ACTION_GROUP)
        except doot.errors.DootError as err:
            self._execute_action_group(task, group=FAIL_GROUP)
            raise

    def _test_conditions(self, task:Task_p) -> bool:
        """ run a task's depends_on group, coercing to a bool
        returns False if the runner should skip the rest of the task
        """
        doot.report.act(info="Check", msg="Preconditions")
        match self._execute_action_group(task, group=DEPENDS_GROUP):
            case None:
                return True
            case _, ActRE.SKIP | ActRE.FAIL:
                return False
            case _:
                return True
