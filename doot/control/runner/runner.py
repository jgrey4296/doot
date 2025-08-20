#!/usr/bin/env python3
"""

"""
# ruff: noqa: N812
# : disable-error-code="attr-defined"
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
import networkx as nx
from jgdv import Mixin, Proto
from jgdv.debugging import NullHandler, SignalHandler

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.control.runner._interface import WorkflowRunner_p
from doot.workflow import (ActionSpec, RelationSpec, TaskArtifact, TaskName, TaskSpec)
from doot.workflow._interface import ActionResponse_e as ActRE
from doot.workflow._interface import Job_p, Task_p, TaskName_p, TaskSpec_i, ActionSpec_i, RelationSpec_i

# ##-- end 1st party imports

# ##-| Local
from . import _interface as API # noqa: N812
from . import util as RU

# # End of Imports.

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
    from doot.control.tracker._interface import WorkflowTracker_p
    from doot.workflow._interface import Artifact_i, DelayedSpec
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|
from typing import ContextManager
# isort: on
# ##-- end types

##-- logging
logging           = logmod.getLogger(__name__)
##-- end logging

##--| Vars
skip_msg            : Final[str]   = doot.constants.printer.skip_by_condition_msg
max_steps           : Final[int]   = doot.config.on_fail(100_000).commands.run.max_steps()
hide_empty_cleanup  : Final[bool]  = doot.config.on_fail(False).commands.run.hide_empty_cleanup()  # noqa: FBT003

SETUP_GROUP         : Final[str]   = "setup"
ACTION_GROUP        : Final[str]   = "actions"
FAIL_GROUP          : Final[str]   = "on_fail"
DEPENDS_GROUP       : Final[str]   = "depends_on"

##--|

class ActionExecutor:
    """ An internal object handling the logic of running action(groups) of a task """

    def execute_action_group(self, task:Task_p, *, group:str, large_step:int) -> Maybe[tuple[int, ActRE, list]]:
        """ Execute a group of actions, possibly queue any task specs they produced,
        and return a count of the actions run + the result
        """
        to_queue        : list[TaskName_p|TaskSpec_i|DelayedSpec]
        group_result    : ActRE
        actions         : Iterable[ActionSpec_i]
        executed_count  : int
        ##--|
        actions  = task.get_action_group(group)

        if not bool(actions):
            return None

        group_result    = ActRE.SUCCESS
        to_queue        =  []
        executed_count  = 0

        for action in self.skip_relation_specs(actions):
            match self.execute_action(large_step, executed_count, action, task, group=group):
                case True | None:
                    continue
                case list() as result:
                    to_queue += result
                case False:
                    group_result = ActRE.FAIL
                    break
                case ActRE.SKIP:
                    doot.report.wf.act("skip", skip_msg)
                    group_result = ActRE.SKIP
                    break

            executed_count += 1

        else: # no break.
            pass

        return executed_count, group_result, to_queue

    def skip_relation_specs(self, actions:Iterable) -> Iterator:
        """ return of True signals the action is a relationspec, so is to be ignored """
        for action in actions:
            match action:
                case RelationSpec():
                    pass
                case ActionSpec() as act:
                    yield act
                case _:
                    raise doot.errors.TaskError("Task Failed: Bad Action: %s", repr(action))

    def execute_action(self, large_step:int, count:int, action:ActionSpec_i, task:Task_p, group:Maybe[str]=None) -> ActRE|list:
        """ Run the given action of a specific task.

          returns either a list of specs to (potentially) queue,
          or an ActRE describing the action result.

        """
        result : ActRE|list
        ##--|
        task.internal_state['_action_step'] = count
        match group:
            case str():
                doot.report.wf.act(f"{large_step}.{group}.{count}", str(action.do))
            case None:
                doot.report.wf.act(f"{large_step}._.{count}", str(action.do))

        logging.debug("Action Executing for Task: %s", task.name)
        logging.debug("Action State: %s.%s: args=%s kwargs=%s. state(size)=%s", large_step, count, action.args, dict(action.kwargs), len(task.internal_state.keys()))
        response = action(task.internal_state)
        match response:
            case None | True:
                result = ActRE.SUCCESS
            case False | ActRE.FAIL:
                raise doot.errors.TaskFailed("Task %s: Action Failed: %s", task.name, action.do, task=task.spec)
            case ActRE.SKIP as result:
                # result will be returned, and expand_job/execute_task will handle it
                pass
            case dict() as data: # update the task's state
                task.internal_state.update({str(k):v for k,v in data.items()})
                result = ActRE.SUCCESS
            case list() as data if isinstance(task, Job_p):
                result = data
            case x:
                raise doot.errors.TaskError("Task %s: Action %s Failed: Returned an unplanned for value: %s", task.name, action.do, x, task=task.spec)

        return result

    def test_conditions(self, task:Task_p, *, large_step:int) -> bool:
        """ run a task's depends_on group, coercing to a bool
        returns False if the runner should skip the rest of the task
        """
        match self.execute_action_group(task, group=DEPENDS_GROUP, large_step=large_step):
            case None:
                return True
            case _, ActRE.SKIP | ActRE.FAIL, _:
                return False
            case _:
                return True
##--|

@Proto(WorkflowRunner_p, check=False)
@Mixin(RU._RunnerCtx_m, RU._RunnerHandlers_m, None)
class DootRunner:
    """ The simplest single threaded task runner """

    large_step     : int
    tracker        : WorkflowTracker_p
    teardown_list  : list
    executor       : ActionExecutor

    def __init__(self:Self, *, tracker:WorkflowTracker_p, executor:Maybe[ActionExecutor]=None):
        super().__init__()
        self.large_step           = 0
        self.tracker        = tracker
        self.executor       = executor or ActionExecutor()
        self.teardown_list  = []                                                                   # list of tasks to teardown

    def __call__(self, *tasks:str, handler:Maybe[API.Handler]=None):  #noqa: ARG002
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

        assert(isinstance(handler, ContextManager))
        with handler:
            while bool(self.tracker) and self.large_step < max_steps:
                self.run_next_task()
            else:
                pass

    def run_next_task(self) -> None:
        """
          Get the next task from the tracker, expand/run it,
          and handle the result/failure
        """
        task : Maybe[Task_p|Artifact_i] = None
        try:
            match (task:=self.tracker.next_for()):
                case None:
                    pass
                case TaskArtifact():
                    self.notify_artifact(task)
                case Job_p():
                    self.expand_job(task)
                case Task_p():
                    self.execute_task(task)
                case x:
                    doot.report.gen.error("Unknown Value provided to runner: %s", x)
        except doot.errors.TaskError as err:
            err.task = task
            self.handle_failure(err)
        except doot.errors.DootError as err:
            self.handle_failure(err)
        except Exception as err:
            doot.report.wf.fail(info="Exception", msg=str(err))
            self.tracker.clear()
            raise
        else:
            self.handle_success(task)
            self.sleep_after(task)
            self.large_step += 1

    def expand_job(self, job:Job_p) -> None:
        """ turn a job into all of its tasks, including teardowns """
        logmod.debug("-- Expanding Job %s: %s", self.large_step, job.name)
        assert(isinstance(job, Job_p))
        try:
            doot.report.wf.branch(job.spec.name, info=f"Job {self.large_step}")
            if not self.executor.test_conditions(job, large_step=self.large_step):
                return

            self.executor.execute_action_group(job, group=SETUP_GROUP, large_step=self.large_step)
            match self.executor.execute_action_group(job, group=ACTION_GROUP, large_step=self.large_step):
                case None:
                    pass
                case int(), ActRE(), [*xs]:
                    self._queue_more_tasks(job.name, xs)
        except doot.errors.DootError as err:
            self.executor.execute_action_group(job, group=FAIL_GROUP, large_step=self.large_step)
            raise

    def execute_task(self, task:Task_p) -> None:
        """ execute a single task's actions """
        logmod.debug("-- Expanding Task %s: %s", self.large_step, task.name)
        assert(not isinstance(task, Job_p))
        try:
            doot.report.wf.branch(task.spec.name, info=f"Task {self.large_step}")
            if not self.executor.test_conditions(task, large_step=self.large_step):
                return

            self.executor.execute_action_group(task, group=SETUP_GROUP, large_step=self.large_step)
            self.executor.execute_action_group(task, group=ACTION_GROUP, large_step=self.large_step)
        except doot.errors.DootError as err:
            self.executor.execute_action_group(task, group=FAIL_GROUP, large_step=self.large_step)
            raise

    def _queue_more_tasks(self, source:TaskName_p, new_tasks:list) -> None:
        """ When 'allowed', an action group can queue more tasks in the tracker,
        can return a new ActRE to describe the result status of this group
        """
        new_nodes : list[TaskName_p] = []
        failures  = []
        for spec in new_tasks:
            match self.tracker.queue(spec):
                case None:
                    failures.append(spec.name)
                case TaskName_p() as x:
                    new_nodes.append(x)

        if bool(failures):
            raise doot.errors.JobExpansionError("Queuing generated specs failed", source, failures)

        if bool(new_nodes):
            self.tracker.build(sources=new_nodes) # type: ignore[arg-type]

    ##--| handlers

    def handle_success[T:Task_p|Artifact_i](self, task:Maybe[T]) -> Maybe[T]:
        raise NotImplementedError()

    def handle_failure(self, failure:Exception) -> None:
        raise NotImplementedError()

    def sleep_after[T:Task_p|Artifact_i](self, task:Maybe[T]) -> None:
        raise NotImplementedError()
