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
import re
import time
import types
from collections import defaultdict
from contextlib import nullcontext
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Self, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import networkx as nx

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import (Action_p, FailPolicy_p, Job_i, Reporter_p, Task_i,
                            TaskRunner_i, TaskTracker_i)
from doot._structs.relation_spec import RelationSpec
from doot.control.base_runner import BaseRunner, logctx
from doot.enums import ActionResponse_e as ActRE
from doot.enums import Report_f
from doot.structs import ActionSpec, TaskArtifact, TaskName, TaskSpec
from doot.utils.signal_handler import SignalHandler

# ##-- end 1st party imports

##-- logging
logging       = logmod.getLogger(__name__)
printer       = logmod.getLogger("doot._printer")
fail_l        = printer.getChild("fail")
skip_l        = printer.getChild("skip")
task_header_l = printer.getChild("task_header")
actgrp_l      = printer.getChild("action_group")
queue_l       = printer.getChild("queue")
actexec_l     = printer.getChild("action_exec")
state_l       = printer.getChild("task_state")
##-- end logging

head_level              : Final[str] = doot.constants.printer.DEFAULT_HEAD_LEVEL
build_level             : Final[str] = doot.constants.printer.DEFAULT_BUILD_LEVEL
action_level            : Final[str] = doot.constants.printer.DEFAULT_ACTION_LEVEL
sleep_level             : Final[str] = doot.constants.printer.DEFAULT_SLEEP_LEVEL
execute_level           : Final[str] = doot.constants.printer.DEFAULT_EXECUTE_LEVEL
skip_msg                : Final[str] = doot.constants.printer.skip_by_condition_msg
actgrp_prefix           : Final[str] = doot.constants.printer.action_group_prefix
fail_prefix             : Final[str] = doot.constants.printer.fail_prefix
max_steps               : Final[str] = doot.config.on_fail(100_000).settings.tasks.max_steps()

@doot.check_protocol
class DootRunner(BaseRunner, TaskRunner_i):
    """ The simplest single threaded task runner """

    def __init__(self:Self, *, tracker:TaskTracker_i, reporter:Reporter_p):
        super().__init__(tracker=tracker, reporter=reporter)
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
            while bool(self.tracker) and self.step < max_steps:
                self._run_next_task()

    def _run_next_task(self):
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
                    raise doot.errors.DootTaskFailed("Artifact resolutely does not exist", task=task)
                case Job_i() if self._test_conditions(task):
                    self._expand_job(task)
                case Task_i() if self._test_conditions(task):
                    self._execute_task(task)
                case Task_i():
                    # test_conditions failed, so skip
                    skip_l.info(skip_msg, self.step, task.shortname)
                case _:
                    pass
        except doot.errors.DootError as err:
            self._handle_failure(task, err)
        except Exception as err:
            fail_l.exception("Unknown, non-Doot failure occurred: %s", err)
            self.tracker.clear_queue()
            raise err
        else:
            self._handle_task_success(task)
            self._sleep(task)
            self.step += 1

    def _expand_job(self, job:Job_i) -> None:
        """ turn a job into all of its tasks, including teardowns """
        try:
            logmod.debug("-- Expanding Job %s: %s", self.step, job.shortname)
            task_header_l.info("> Job %s: %s", self.step, job.shortname, extra={"colour":"magenta"})
            self.reporter.add_trace(job.spec, flags=Report_f.JOB | Report_f.INIT)

            self._execute_action_group(job.spec.setup, job, group="setup")
            self._execute_action_group(job.spec.actions, job, allow_queue=True, group="actions")

        except doot.errors.DootError as err:
            self._execute_action_group(job.spec.on_fail, job, group="on_fail")
            raise err
        finally:
            # cleanup actions are *not* run here, as they've been added to the auto-gen $head$ and queued
            job.state.clear()
            self.reporter.add_trace(job.spec, flags=Report_f.JOB | Report_f.SUCCEED)
            task_header_l.info("< Job %s: %s", self.step, job.shortname, extra={"colour":"magenta"})

    def _execute_task(self, task:Task_i) -> None:
        """ execute a single task's actions """
        try:
            task_header_l.info("> Task %s :  %s", self.step, task.shortname, extra={"colour":"magenta"})
            self.reporter.add_trace(task.spec, flags=Report_f.TASK | Report_f.INIT)

            self._execute_action_group(task.spec.setup, task, group="setup")
            self._execute_action_group(task.spec.actions, task, group="action")
            self.reporter.add_trace(task.spec, flags=Report_f.TASK | Report_f.SUCCEED)
        except doot.errors.DootError as err:
            self._execute_action_group(task.spec.on_fail, task, group="on_fail")
            raise err
        finally:
            # Cleanup Actions *are* run here, because tasks don't have subtasks they setup for
            self._execute_action_group(task.spec.cleanup, task, group="cleanup")
            task.state.clear()
            task_header_l.debug("< Task: %s", task.shortname, extra={"colour":"cyan"})

    def _execute_action_group(self, actions:list, task:Task_i, allow_queue=False, group=None) -> tuple[int, ActRE]:
        """ Execute a group of actions, possibly queue any task specs they produced,
        and return a count of the actions run + the result
        """
        actgrp_l.info("%s Action Group %s (%s) for : %s", actgrp_prefix, group, len(actions), task.shortname)
        group_result     = ActRE.SUCCESS
        to_queue         = []
        executed_count   = 0

        for action in actions:
            result : None|bool|list = None
            match action:
                case RelationSpec():
                    pass
                case ActionSpec():
                    result = self._execute_action(executed_count, action, task)
                case _:
                    self.reporter.add_trace(task.spec, flags=Report_f.FAIL | Report_f.TASK)
                    raise doot.errors.DootTaskError("Task %s Failed: Produced a bad action: %s", task.shortname, repr(action), task=task.spec)

            match result:
                case True:
                    continue
                case False:
                    group_result = ActRE.FAIL
                    break
                case None:
                    continue
                case list():
                    to_queue += result
                case ActRE.SKIP:
                    skip_l.warning("------ Remaining Task Actions skipped by Action Result")
                    group_result = ActRE.SKIP
                    break

            executed_count += 1

        else: # runs only if no 'break'
            match to_queue:
                case []:
                    pass
                case [*xs] if not allow_queue:
                    fail_l.warning("%s Tried to Queue additional tasks from a bad action group: %s", fail_prefix, task)
                    group_result = ActRE.FAIL
                case [*xs]:
                    new_nodes = []
                    for spec in xs:
                        match self.tracker.queue_entry(spec):
                            case None:
                                queue_l.warning("Queuing a generated spec failed: %s", spec.name)
                            case TaskName() as x:
                                new_nodes.append(x)
                    self.tracker.build_network(sources=new_nodes)
                    queue_l.info("Queued %s Subtasks for %s", len(xs), task.shortname)

        return executed_count, group_result

    def _execute_action(self, count, action, task) -> ActRE|list:
        """ Run the given action of a specific task.

          returns either a list of specs to (potentially) queue,
          or an ActRE describing the action result.

        """
        result                     = None
        task.state['_action_step'] = count
        self.reporter.add_trace(action, flags=Report_f.ACTION | Report_f.INIT)
        actexec_l.info( "Action %s.%s: %s", self.step, count, action.do or action.fun, extra={"colour":"cyan"})

        actexec_l.debug("Action Executing for Task: %s", task.shortname)
        actexec_l.debug("Action State: %s.%s: args=%s kwargs=%s. state(size)=%s", self.step, count, action.args, dict(action.kwargs), len(task.state.keys()))
        action.verify(task.state)
        result = action(task.state)
        actexec_l.debug("Action Result: %s", result)

        match result:
            case ActRE.SKIP:
                # result will be returned, and expand_job/execute_task will handle it
                pass
            case None | True:
                result = ActRE.SUCCESS
            case dict(): # update the task's state
                state_l.info("Updating Task State: %s keys", len(result))
                task.state.update({str(k):v for k,v in result.items()})
                result = ActRE.SUCCESS
            case list() if all(isinstance(x, (TaskName, TaskSpec)) for x in result):
                pass
            case False | ActRE.FAIL:
                self.reporter.add_trace(action, flags=Report_f.FAIL | Report_f.ACTION)
                raise doot.errors.DootTaskFailed("Task %s: Action Failed: %s", task.shortname, action.do, task=task.spec)
            case _:
                self.reporter.add_trace(action, flags=Report_f.FAIL | Report_f.ACTION)
                raise doot.errors.DootTaskError("Task %s: Action %s Failed: Returned an unplanned for value: %s", task.shortname, action.do, result, task=task.spec)

        action.verify_out(task.state)
        self.reporter.add_trace(action, flags=Report_f.ACTION | Report_f.SUCCEED)
        return result

    def _test_conditions(self, task:Task_i) -> bool:
        """ run a task's depends_on group, coercing to a bool """
        match self._execute_action_group(task.spec.depends_on, task, group="depends_on"):
            case _, ActRE.SKIP | ActRE.FAIL:
                return False
            case _, _:
                return True
