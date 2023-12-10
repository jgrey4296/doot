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
import doot
import doot.constants
import doot.errors
from doot.enums import ReportEnum, ActionResponseEnum as ActRE
from doot._abstract import Tasker_i, Task_i, FailPolicy_p
from doot._abstract import TaskTracker_i, TaskRunner_i, TaskBase_i, ReportLine_i, Action_p, Reporter_i
from doot.structs import DootTaskArtifact
from doot.utils.signal_handler import SignalHandler
from doot.structs import DootTaskSpec, DootActionSpec

dry_run                    = doot.args.on_fail(False).cmd.args.dry_run()
head_level    : Final[str] = doot.constants.DEFAULT_HEAD_LEVEL
build_level   : Final[str] = doot.constants.DEFAULT_BUILD_LEVEL
action_level  : Final[str] = doot.constants.DEFAULT_ACTION_LEVEL
sleep_level   : Final[str] = doot.constants.DEFAULT_SLEEP_LEVEL
execute_level : Final[str] = doot.constants.DEFAULT_EXECUTE_LEVEL

@doot.check_protocol
class DootRunner(TaskRunner_i):
    """ The simplest single threaded task runner """

    def __init__(self:Self, *, tracker:TaskTracker_i, reporter:Reporter_i, policy=None):
        super().__init__(tracker=tracker, reporter=reporter, policy=policy)
        self._printer_level_stack = []
        self.step                 = 0
        self.default_SLEEP_LENGTH = doot.config.on_fail(0.2, int|float).settings.tasks.sleep.task()

    def __enter__(self) -> Any:
        printer.info("---------- Task Loop Starting ----------", extra={"colour" : "green"})
        return


    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        self._set_print_level("INFO")
        printer.info("")
        printer.info("---------- Task Loop Finished ----------", extra={"colour":"green"})
        self._finish()
        return


    def __call__(self, *tasks:str):
        """ tasks are initial targets to run.
          so loop on the tracker, getting the next task,
          running its actions,
          and repeating,
          until done

          if task is a tasker, it is expanded and added into the tracker
          """
        # TODO for threaded tasks: replace expand_tasker/execute_task/execute_action with twisted?

        with SignalHandler():
            self._set_print_level("INFO")
            for task in iter(self.tracker):
                if task is None:
                    continue

                try:
                    match task:
                        case DootTaskArtifact():
                            self._notify_artifact(task)
                            continue
                        case Tasker_i():
                            self._expand_tasker(task)
                        case Task_i():
                            self._execute_task(task)

                    self._set_print_level(task.spec.print_levels.on_fail(sleep_level).sleep())
                    self.tracker.update_state(task, self.tracker.state_e.SUCCESS)
                    sleep_len = task.spec.extra.on_fail(self.default_SLEEP_LENGTH, int|float).sleep()
                    printer.info("[Sleeping (%s)...]", sleep_len, extra={"colour":"white"})
                    time.sleep(sleep_len)
                    self.step += 1
                # Handle problems:
                except doot.errors.DootTaskInterrupt as err:
                    breakpoint()
                except doot.errors.DootTaskTrackingError as err:
                    self.reporter.trace(task.spec, flags=ReportEnum.FAIL)
                    pass
                except doot.errors.DootTaskFailed as err:
                    printer.warning("Task Failed: %s : %s", task.name, err)
                    self.tracker.update_state(task, self.tracker.state_e.FAILED)
                except doot.errors.DootTaskError as err:
                    printer.warning("Task Error : %s : %s", task.name, err)
                    self.tracker.update_state(task, self.tracker.state_e.FAILED)
                except doot.errors.DootError as err:
                    printer.warning("Doot Error : %s : %s", task.name, err)
                    self.tracker.update_state(task, self.tracker.state_e.FAILED)

                self._set_print_level("INFO")

    def _notify_artifact(self, art:DootTaskArtifact) -> None:
        printer.info("---- Artifact: %s", art)
        self.reporter.trace(art, flags=ReportEnum.ARTIFACT)

    def _expand_tasker(self, tasker:Tasker_i) -> None:
        """ turn a tasker into all of its tasks, including teardowns """
        logmod.debug("-- Expanding Tasker %s: %s", self.step, tasker.name)
        self._set_print_level(tasker.spec.print_levels.on_fail(head_level).head())
        printer.info("---- Tasker %s: %s", self.step, tasker.name, extra={"colour":"magenta"})
        if bool(tasker.spec.actions):
            printer.warning("-- Tasker %s: Actions were found in tasker spec, but taskers don't run actions")
        self.reporter.trace(tasker.spec, flags=ReportEnum.TASKER | ReportEnum.INIT)
        count = 0
        self._set_print_level(tasker.spec.print_levels.on_fail(build_level).build())
        for task in tasker.build():
            match task:
                case Tasker_i():
                    printer.warning("Taskers probably shouldn't build taskers: %s : %s", tasker.name, task.name)
                    self.tracker.add_task(task, no_root_connection=True)
                    self.tracker.queue_task(task.name)
                case Task_i():
                    self.tracker.add_task(task, no_root_connection=True)
                    self.tracker.queue_task(task.name)
                case DootTaskSpec():
                    self.tracker.add_task(task, no_root_connection=True)
                    self.tracker.queue_task(task.name)
                case _:
                    self.reporter.trace(tasker.spec, flags=ReportEnum.FAIL | ReportEnum.TASKER)
                    raise doot.errors.DootTaskError("Tasker %s Built a Bad Value: %s", tasker.name, task, task=tasker.spec)

            count += 1

        logmod.debug("-- Tasker %s Expansion produced: %s tasks", tasker.name, count)
        self.reporter.trace(tasker.spec, flags=ReportEnum.TASKER | ReportEnum.SUCCEED)

    def _execute_task(self, task:Task_i) -> None:
        """ execute a single task's actions """
        logmod.debug("---- Executing Task %s: %s", self.step, task.name)
        self._set_print_level(task.spec.print_levels.on_fail(head_level).head())
        printer.info("---- Task %s: %s", self.step, task.name, extra={"colour":"magenta"})
        self.reporter.trace(task.spec, flags=ReportEnum.TASK | ReportEnum.INIT)
        # TODO <-- in the future, where DB checks for staleness, thread safety, etc will occur

        action_count = 0
        action_result = ActRE.SUCCESS
        self._set_print_level(task.spec.print_levels.on_fail(build_level).build())
        for action in task.actions:
            match action:
                case _ if dry_run:
                    logging.info("Dry Run: Not executing action: %s : %s", task.name, action, extra={"colour":"cyan"})
                    self.reporter.trace(task.spec, flags=ReportEnum.ACTION | ReportEnum.SKIP)
                case DootActionSpec() if action.fun is None:
                    self.reporter.trace(task.spec, flags=ReportEnum.FAIL | ReportEnum.TASK)
                    raise doot.errors.DootTaskError("Task %s Failed: Produced an action with no callable: %s", task.name, action, task=task.spec)
                case DootActionSpec():
                    action_result = self._execute_action(action_count, action, task)
                case _:
                    self.reporter.trace(task.spec, flags=ReportEnum.FAIL | ReportEnum.TASK)
                    raise doot.errors.DootTaskError("Task %s Failed: Produced a bad action: %s", task.name, action, task=task.spec)

            self._set_print_level(task.spec.print_levels.on_fail(build_level).build())
            action_count += 1
            if action_result is ActRE.SKIP:
                printer.info("------ Remaining Task Actions skipped by Action Instruction")
                break
        else: # Only try to add more tasks if the actions completed successfully, and weren't skipped
            self._set_print_level(task.spec.print_levels.on_fail(build_level).build())
            printer.info("")
            printer.debug("------ Task %s: Actions Complete", task.name, extra={"colour":"cyan"})
            self.reporter.trace(task.spec, flags=ReportEnum.TASK | ReportEnum.SUCCEED)
            # Get Any resulting tasks
            count = 0
            for new_task in task.maybe_more_tasks():
                match new_task:
                    case DootTaskSpec():
                        self.tracker.add_task(new_task, no_root_connection=True)
                        count += 1
                    case Task_i():
                        self.tracker.add_task(new_task, no_root_connection=True)
                        count += 1
                    case _:
                        self.reporter.trace(task.spec, flags=ReportEnum.FAIL | ReportEnum.TASK)
                        raise doot.errors.DootTaskError("Task %s Failed: Provided a bad additional task: %s", task.name, new_task, task=task.spec)
            else:
                logmod.debug("------ Task Execution Completed: %s, adding %s additional tasks", task.name, count)

        printer.debug("------ Task Executed %s Actions", action_count)

    def _execute_action(self, count, action, task) -> ActRE:
        """ Run the given action of a specific task  """
        logmod.debug("------ Executing Action %s: %s for %s", count, action, task.name)
        self._set_print_level(task.spec.print_levels.on_fail(action_level).action())
        self.reporter.trace(action, flags=ReportEnum.ACTION | ReportEnum.INIT)
        task.state['_action_step'] = count
        printer.info("------ Action %s.%s: %s", self.step, count, action.do, extra={"colour":"cyan"})
        printer.debug("------ Action %s.%s: args=%s kwargs=%s. state keys = %s", self.step, count, action.args, dict(action.kwargs), list(task.state.keys()))
        action.verify(task.state)

        self._set_print_level(task.spec.print_levels.on_fail(execute_level).execute())
        result = action(task.state)
        self._set_print_level(task.spec.print_levels.on_fail(action_level).action())
        printer.debug("-- Action Result: %s", result)
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

    def _finish(self):
        """finish running tasks, summarizing results"""
        logging.info("Task Running Completed")
        printer.info("Final Summary: ")
        printer.info(str(self.reporter), extra={"colour":"magenta"})


    def _set_print_level(self, level=None):
        """
        Utility to set the print level, or reset it if no level is specified.
        the Step Runner subclass overrides this to allow interactive control of the print level
        """
        if level:
            printer.setLevel(level)
