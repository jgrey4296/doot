#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

# import abc
# import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Self)
# from uuid import UUID, uuid1
# from weakref import ref

import networkx as nx
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

from collections import defaultdict
from contextlib import nullcontext
import doot
import doot.errors
from doot.enums import ReportEnum, ActionResponseEnum as ActRE
from doot._abstract import Job_i, Task_i, FailPolicy_p
from doot._abstract import TaskTracker_i, TaskRunner_i, Task_i, ReportLine_i, Action_p, Reporter_i
from doot.structs import DootTaskArtifact, DootTaskSpec, DootActionSpec, DootTaskName
from doot.control.base_runner import BaseRunner, logctx
from doot.utils.signal_handler import SignalHandler

head_level    : Final[str] = doot.constants.printer.DEFAULT_HEAD_LEVEL
build_level   : Final[str] = doot.constants.printer.DEFAULT_BUILD_LEVEL
action_level  : Final[str] = doot.constants.printer.DEFAULT_ACTION_LEVEL
sleep_level   : Final[str] = doot.constants.printer.DEFAULT_SLEEP_LEVEL
execute_level : Final[str] = doot.constants.printer.DEFAULT_EXECUTE_LEVEL
max_steps     : Final[str] = doot.config.on_fail(100_000).settings.tasks.max_steps()

@doot.check_protocol
class DootRunner(BaseRunner, TaskRunner_i):
    """ The simplest single threaded task runner """

    def __init__(self:Self, *, tracker:TaskTracker_i, reporter:Reporter_i, policy=None):
        super().__init__(tracker=tracker, reporter=reporter, policy=policy)
        self.teardown_list  = []                     # list of tasks to teardown

    def __call__(self, *tasks:str, handler=None):
        """ tasks are initial targets to run.
          so loop on the tracker, getting the next task,
          running its actions,
          and repeating,
          until done

          if task is a job, it is expanded and added into the tracker
          """
        match handler:
            case None | True:
                handler = SignalHandler()
            case type() as x:
                handler = x()
            case x if hasattr(x, "__enter__"):
                handler = x
            case _:
                handler = nullcontext()

        with handler:
            printer.setLevel("INFO")
            while bool(self.tracker) and self.step < max_steps:
                self._run_next_task()

    def _run_next_task(self):
        """
          Get the next task from the tracker, expand/run it,
          and handle the result/failure
        """
        with logctx("INFO"):
            task = None
            try:
                match (task:= self.tracker.next_for()):
                    case None:
                        pass
                    case DootTaskArtifact():
                        self._notify_artifact(task)
                    case Job_i() if self._test_conditions(task):
                        self._expand_job(task)
                    case Task_i() if self._test_conditions(task):
                        self._execute_task(task)
                    case Task_i():
                        # test_conditions failed, so skip
                        printer.info("----| Task %s: %s Skipped.", self.step, task.spec.name)
                    case _:
                        pass
            except doot.errors.DootError as err:
                self._handle_failure(task, err)
            except Exception as err:
                printer.exception("Unknown, non-Doot failure occurred: %s", err)
                self.tracker.clear_queue()
                raise err
            else:
                self._handle_task_success(task)
                self._sleep(task)
                self.step += 1

    def _expand_job(self, job:Job_i) -> None:
        """ turn a job into all of its tasks, including teardowns """
        build_log_level  = job.spec.print_levels.on_fail(build_level).build()
        head_log_level   = job.spec.print_levels.on_fail(head_level).head()

        try:
            logmod.debug("-- Expanding Job %s: %s", self.step, job.name)
            with logctx(head_log_level) as p:     # Announce entry
                p.info("---> Job %s: %s", self.step, job.name, extra={"colour":"magenta"})
                # TODO queue $head$

            self.reporter.add_trace(job.spec, flags=ReportEnum.JOB | ReportEnum.INIT)

            with logctx(build_log_level) as p: # Run the actions
                self._execute_action_group(job.spec.setup, job, group="setup")
                self._execute_action_group(job.spec.actions, job, allow_queue=True, group="actions")

        except doot.errors.DootError as err:
            self._execute_action_group(job.spec.on_fail, job, group="on_fail")
            raise err
        finally:
            # cleanup actions are *not* run here, as they've been added to the auto-gen $head$ and queued
            job.state.clear()

            with logctx(head_log_level)  as p: # Announce Exit
                self.reporter.add_trace(job.spec, flags=ReportEnum.JOB | ReportEnum.SUCCEED)
                p.info("---< Job %s: %s", self.step, job.name, extra={"colour":"magenta"})

    def _execute_task(self, task:Task_i) -> None:
        """ execute a single task's actions """
        build_log_level  = task.spec.print_levels.on_fail(build_level).build()
        head_log_level   = task.spec.print_levels.on_fail(head_level).head()

        try:
            with logctx(head_log_level) as p: # Announce entry
                p.info("----> Task %s :  %s", self.step, task.spec.name.readable, extra={"colour":"magenta"})

            self.reporter.add_trace(task.spec, flags=ReportEnum.TASK | ReportEnum.INIT)

            with logctx(build_log_level) as p: # Build then run actions
                self._execute_action_group(task.spec.setup, task, group="setup")
                self._execute_action_group(task.spec.actions, task, group="action")
                self.reporter.add_trace(task.spec, flags=ReportEnum.TASK | ReportEnum.SUCCEED)
        except doot.errors.DootError as err:
            self._execute_action_group(task.spec.on_fail, task, group="on_fail")
            raise err
        finally:
            # Cleanup Actions *are* run here, because tasks don't have subtasks they setup for
            self._execute_action_group(task.spec.cleanup, task, group="cleanup")
            task.state.clear()

            with logctx(head_log_level)  as p: # Cleanup and exit
                p.debug("----< Task: %s", task.name, extra={"colour":"cyan"})

    def _execute_action_group(self, actions:list, task:Task_i, allow_queue=False, group=None) -> tuple[int, ActRE]:
        """ Execute a group of actions, possibly queue any task specs they produced,
        and return a count of the actions run + the result
        """
        logging.debug("Running Action Group %s (%s) for : %s", group, len(actions), task.spec.name)
        group_result     = ActRE.SUCCESS
        to_queue         = []
        executed_count   = 0

        for action in actions:
            result = None
            match action:
                case DootActionSpec():
                    result = self._execute_action(executed_count, action, task)
                case DootTaskArtifact():
                    pass
                case DootTaskName():
                    pass
                case _:
                    self.reporter.add_trace(task.spec, flags=ReportEnum.FAIL | ReportEnum.TASK)
                    raise doot.errors.DootTaskError("Task %s Failed: Produced a bad action: %s", task.name, action, task=task.spec)

            match result:
                case None:
                    continue
                case list():
                    to_queue += result
                case ActRE.SKIP:
                    printer.warning("------ Remaining Task Actions skipped by Action Result")
                    group_result = ActRE.SKIP
                    break

            executed_count += 1

        else: # runs only if no 'break'
            match to_queue:
                case []:
                    pass
                case [*xs] if not allow_queue:
                    printer.warning("---- !!!! Tried to Queue additional tasks from a bad action group: %s", task)
                    group_result = ActRE.FAIL
                case [*xs]:
                    for spec in xs:
                        self.tracker.add_task(spec, no_root_connection=True)
                    printer.info("Queued %s Subtasks for %s", len(xs), task.spec.name)

        return executed_count, group_result

    def _execute_action(self, count, action, task) -> ActRE|list:
        """ Run the given action of a specific task.

          returns either a list of specs to (potentially) queue,
          or an ActRE describing the action result.

        """
        result                     = None
        action_log_level           = task.spec.print_levels.on_fail(action_level).action()
        execute_log_level          = task.spec.print_levels.on_fail(execute_level).execute()
        task.state['_action_step'] = count
        self.reporter.add_trace(action, flags=ReportEnum.ACTION | ReportEnum.INIT)
        logmod.debug("-----> Action Execution: %s for %s", action, task.name)

        with logctx(action_log_level) as p: # Prep the action
            p.info( "-----> Action %s.%s: %s", self.step, count, action.do, extra={"colour":"cyan"})
            p.debug("-----> Action %s.%s: args=%s kwargs=%s. state keys = %s", self.step, count, action.args, dict(action.kwargs), list(task.state.keys()))
            action.verify(task.state)

            with logctx(execute_log_level) as p2: # call the action
                result = action(task.state)
                ##
            p.debug("-- Action Result: %s", result)

        with logctx(action_log_level) as p: # Handle the result
            match result:
                case ActRE.SKIP:
                    # result will be returned, and expand_job/execute_task will handle it
                    pass
                case None | True:
                    result = ActRE.SUCCESS
                case dict(): # update the task's state
                    task.state.update({str(k):v for k,v in result.items()})
                    result = ActRE.SUCCESS
                case list() if all(isinstance(x, (DootTaskName, DootTaskSpec)) for x in result):
                    pass
                case False | ActRE.FAIL:
                    self.reporter.add_trace(action, flags=ReportEnum.FAIL | ReportEnum.ACTION)
                    raise doot.errors.DootTaskFailed("Task %s: Action Failed: %s", task.name, action.do, task=task.spec)
                case _:
                    self.reporter.add_trace(action, flags=ReportEnum.FAIL | ReportEnum.ACTION)
                    raise doot.errors.DootTaskError("Task %s: Action %s Failed: Returned an unplanned for value: %s", task.name, action.do, result, task=task.spec)

            action.verify_out(task.state)

        with logctx(action_log_level) as p: # Prep the action
            p.debug("-----< Action Execution Complete: %s for %s", action, task.name)

        self.reporter.add_trace(action, flags=ReportEnum.ACTION | ReportEnum.SUCCEED)
        return result

    def _test_conditions(self, task:Task_i) -> bool:
        """ run a task's depends_on group, coercing to a bool """
        match self._execute_action_group(task.spec.depends_on, task, group="depends_on"):
            case _, ActRE.SKIP | ActRE.FAIL:
                return False
            case _, _:
                return True
