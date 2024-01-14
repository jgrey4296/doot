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
##-- end logging

printer = logmod.getLogger("doot._printer")

from collections import defaultdict
from contextlib import nullcontext
import doot
import doot.constants
import doot.errors
from doot.enums import ReportEnum, ActionResponseEnum as ActRE
from doot._abstract import Job_i, Task_i, FailPolicy_p
from doot._abstract import TaskTracker_i, TaskRunner_i, TaskBase_i, ReportLine_i, Action_p, Reporter_i
from doot.structs import DootTaskArtifact
from doot.structs import DootTaskSpec, DootActionSpec
from doot.control.base_runner import BaseRunner, logctx
from doot.utils.signal_handler import SignalHandler

dry_run                    = doot.args.on_fail(False).cmd.args.dry_run()
head_level    : Final[str] = doot.constants.DEFAULT_HEAD_LEVEL
build_level   : Final[str] = doot.constants.DEFAULT_BUILD_LEVEL
action_level  : Final[str] = doot.constants.DEFAULT_ACTION_LEVEL
sleep_level   : Final[str] = doot.constants.DEFAULT_SLEEP_LEVEL
execute_level : Final[str] = doot.constants.DEFAULT_EXECUTE_LEVEL
max_steps     : Final[str] = doot.config.on_fail(100_000).settings.general.max_steps()

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
            case x if hasattr(x, "__enter__"):
                handler = x
            case _:
                handler = nullcontext()

        with handler:
            printer.setLevel("INFO")
            while bool(self.tracker) and self.step < max_steps:
                self._run_next_task()

    def _run_next_task(self):
        with logctx("INFO"):
            try:
                match (task:= self.tracker.next_for()):
                    case None:
                        pass
                    case DootTaskArtifact():
                        self._notify_artifact(task)
                    case Job_i():
                        self._expand_job(task)
                    case Task_i():
                        self._execute_task(task)

                self._handle_task_success(task)
                self._sleep(task)

            except doot.errors.DootError as err:
                self._handle_failure(err)



    def _expand_job(self, job:Job_i) -> None:
        """ turn a job into all of its tasks, including teardowns """
        logmod.debug("-- Expanding Job %s: %s", self.step, job.name)
        with logctx(job.spec.print_levels.on_fail(head_level).head()) as p:
            p.info("---- Job %s: %s", self.step, job.name, extra={"colour":"magenta"})

            if bool(job.spec.actions): # and job != mini...
                p.warning("-- Job %s: Actions were found in job spec, but jobs don't run actions", job.name)

        self.reporter.trace(job.spec, flags=ReportEnum.JOB | ReportEnum.INIT)

        count = 0
        with logctx(job.spec.print_levels.on_fail(build_level).build()) as p:
            for task in job.build():
                match task:
                    case Job_i():
                        p.warning("Jobs probably shouldn't build jobs: %s : %s", job.name, task.name)
                        self.tracker.add_task(task, no_root_connection=True)
                    case Task_i():
                        self.tracker.add_task(task, no_root_connection=True)
                    case DootTaskSpec():
                        self.tracker.add_task(task, no_root_connection=True)
                    case _:
                        self.reporter.trace(job.spec, flags=ReportEnum.FAIL | ReportEnum.JOB)
                        raise doot.errors.DootTaskError("Job %s Built a Bad Value: %s", job.name, task, task=job.spec)

                count += 1

        logmod.debug("-- Job %s Expansion produced: %s tasks", job.name, count)
        self.reporter.trace(job.spec, flags=ReportEnum.JOB | ReportEnum.SUCCEED)

    def _execute_task(self, task:Task_i) -> None:
        """ execute a single task's actions """
        with logctx(task.spec.print_levels.on_fail(head_level).head()) as p:
            p.info("---- Task %s: %s", self.step, task.name, extra={"colour":"magenta"})

        self.reporter.trace(task.spec, flags=ReportEnum.TASK | ReportEnum.INIT)

        action_count = 0
        action_result = ActRE.SUCCESS
        with logctx(task.spec.print_levels.on_fail(build_level).build()) as p:
            for action in task.actions:
                match action:
                    case DootActionSpec() if action.fun is None:
                        self.reporter.trace(task.spec, flags=ReportEnum.FAIL | ReportEnum.TASK)
                        raise doot.errors.DootTaskError("Task %s Failed: Produced an action with no callable: %s", task.name, action, task=task.spec)
                    case DootActionSpec():
                        action_result = self._execute_action(action_count, action, task)
                    case _:
                        self.reporter.trace(task.spec, flags=ReportEnum.FAIL | ReportEnum.TASK)
                        raise doot.errors.DootTaskError("Task %s Failed: Produced a bad action: %s", task.name, action, task=task.spec)

                action_count += 1
                if action_result is ActRE.SKIP:
                    p.info("------ Remaining Task Actions skipped by Action Instruction")
                    break

            self.reporter.trace(task.spec, flags=ReportEnum.TASK | ReportEnum.SUCCEED)
            p.debug("------ Task %s: Actions Complete", task.name, extra={"colour":"cyan"})
            p.debug("------ Task Executed %s Actions", action_count)

    def _execute_action(self, count, action, task) -> ActRE:
        """ Run the given action of a specific task  """
        if dry_run:
            logging.info("Dry Run: Not executing action: %s : %s", task.name, action, extra={"colour":"cyan"})
            self.reporter.trace(task.spec, flags=ReportEnum.ACTION | ReportEnum.SKIP)
            return ActRe.SUCCESS

        result = None
        with logctx(task.spec.print_levels.on_fail(action_level).action()) as p:
            self.reporter.trace(action, flags=ReportEnum.ACTION | ReportEnum.INIT)
            task.state['_action_step'] = count
            p.info("------ Action %s.%s: %s", self.step, count, action.do, extra={"colour":"cyan"})
            p.debug("------ Action %s.%s: args=%s kwargs=%s. state keys = %s", self.step, count, action.args, dict(action.kwargs), list(task.state.keys()))
            action.verify(task.state)

            with logctx(task.spec.print_levels.on_fail(execute_level).execute()) as p2:
                ## Actually call the action here:
                result = action(task.state)
                ##
            p.debug("-- Action Result: %s", result)

        match result:
            case ActRE.SKIP:
                pass
            case None | True:
                result = ActRE.SUCCESS
            case dict():
                task.state.update(result)
                result = ActRE.SUCCESS
            case False | ActRE.FAIL:
                self.reporter.trace(action, flags=ReportEnum.FAIL | ReportEnum.ACTION)
                raise doot.errors.DootTaskFailed("Task %s Action Failed: %s", task.name, action, task=task.spec)
            case _:
                self.reporter.trace(action, flags=ReportEnum.FAIL | ReportEnum.ACTION)
                raise doot.errors.DootTaskError("Task %s Action %s Failed: Returned an unplanned for value: %s", task.name, action, result, task=task.spec)

        action.verify_out(task.state)

        logmod.debug("------ Action Execution Complete: %s for %s", action, task.name)
        self.reporter.trace(action, flags=ReportEnum.ACTION | ReportEnum.SUCCEED)
        return result
