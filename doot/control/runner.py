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

# from bs4 import BeautifulSoup
# import boltons
# import construct as C
# import dirty-equals as deq
# import graphviz
# import matplotlib.pyplot as plt
# import more_itertools as itzplus
import networkx as nx
# import numpy as np
# import pandas
# import pomegranate as pom
# import pony import orm
# import pronouncing
# import pyparsing as pp
# import rich
# import seaborn as sns
# import sklearn
# import stackprinter # stackprinter.set_excepthook(style='darkbg2')
# import sty
# import sympy
# import tomllib
# import toolz
# import tqdm
# import validators
# import z3
# import spacy # nlp = spacy.load("en_core_web_sm")

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

from collections import defaultdict
import doot
import doot.errors
from doot.enums import TaskStateEnum, ReportEnum
from doot._abstract import Tasker_i, Task_i, FailPolicy_p
from doot._abstract import TaskTracker_i, TaskRunner_i, TaskBase_i, ReportLine_i, Action_p, Reporter_i
from doot.utils.signal_handler import SignalHandler
from doot.structs import DootTaskSpec, DootActionSpec

dry_run      = doot.args.on_fail(False).cmd.args.dry_run()
SLEEP_LENGTH = doot.config.on_fail(0.2, int|float).settings.general.task.sleep()

@doot.check_protocol
class DootRunner(TaskRunner_i):
    """ The simplest single threaded task runner """

    def __init__(self:Self, *, tracker:TaskTracker_i, reporter:Reporter_i, policy=None):
        super().__init__(tracker=tracker, reporter=reporter, policy=policy)
        self.original_print_level = printer.level
        self.step = 0


    def __enter__(self) -> Any:
        printer.info("---------- Task Loop Starting ----------", extra={"colour" : "green"})
        return


    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        printer.setLevel(self.original_print_level)
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

        self.original_print_level = printer.level
        with SignalHandler():
            for task in iter(self.tracker):
                if task is None:
                    continue

                try:
                    printer.setLevel(task.spec.print_level)
                    match task:
                        case Tasker_i():
                            self._expand_tasker(task)
                        case Task_i():
                            self._execute_task(task)

                    self.tracker.update_state(task, TaskStateEnum.SUCCESS)
                    printer.debug("Sleeping...", extra={"colour":"white"})
                    time.sleep(SLEEP_LENGTH)
                    self.step += 1
                # Handle problems:
                except doot.errors.DootTaskInterrupt as err:
                    breakpoint()
                except doot.errors.DootTaskTrackingError as err:
                    self.reporter.trace(task.spec, flags=ReportEnum.FAIL)
                    pass
                except doot.errors.DootTaskFailed as err:
                    printer.warning("Task Failed: %s : %s", task.name, err)
                    self.tracker.update_state(task, TaskStateEnum.FAILED)
                except doot.errors.DootTaskError as err:
                    printer.warning("Task Error : %s : %s", task.name, err)
                    self.tracker.update_state(task, TaskStateEnum.FAILED)
                except doot.errors.DootError as err:
                    printer.warning("Doot Error : %s : %s", task.name, err)
                    self.tracker.update_state(task, TaskStateEnum.FAILED)
                except Exception as err:
                    self.reporter.trace(task.spec, flags = ReportEnum.TASK | ReportEnum.FAIL)
                    raise err

            printer.setLevel(self.original_print_level)



    def _expand_tasker(self, tasker:Tasker_i) -> None:
        """ turn a tasker into all of its tasks, including teardowns """
        logmod.debug("-- Expanding Tasker %s: %s", self.step, tasker.name)
        printer.info("-- Tasker %s: %s", self.step, tasker.name, extra={"colour":"magenta"})
        self.reporter.trace(tasker.spec, flags=ReportEnum.TASKER | ReportEnum.INIT)
        count = 0
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
        printer.info("---- Task %s: %s", self.step, task.name, extra={"colour":"magenta"})
        self.reporter.trace(task.spec, flags=ReportEnum.TASK | ReportEnum.INIT)
        # TODO <-- in the future, where DB checks for staleness, thread safety, etc will occur

        action_count = 0
        for action in task.actions:
            match action:
                case _ if dry_run:
                    logging.info("Dry Run: Not executing action: %s : %s", task.name, action, extra={"colour":"cyan"})
                    self.reporter.trace(task.spec, flags=ReportEnum.ACTION | ReportEnum.SKIP)
                case DootActionSpec() if action.fun is None:
                    self.reporter.trace(task.spec, flags=ReportEnum.FAIL | ReportEnum.TASK)
                    raise doot.errors.DootTaskError("Task %s Failed: Produced an action with no callable: %s", task.name, action, task=task.spec)
                case DootActionSpec():
                    self._execute_action(action_count, action, task)
                case _:
                    self.reporter.trace(task.spec, flags=ReportEnum.FAIL | ReportEnum.TASK)
                    raise doot.errors.DootTaskError("Task %s Failed: Produced a bad action: %s", task.name, action, task=task.spec)
            action_count += 1

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


        logmod.debug("---- Task Execution Completed: %s, adding %s additional tasks", task.name, count)

    def _execute_action(self, count, action, task) -> None:
        """ Run the given action of a specific task  """
        logmod.debug("------ Executing Action %s: %s for %s", count, action, task.name)
        printer.info("------ Action %s.%s: %s", self.step, count, str(action), extra={"colour":"cyan"})
        self.reporter.trace(action, flags=ReportEnum.ACTION | ReportEnum.INIT)
        task.state['_action_step'] = count
        action.verify(task.state)

        # TODO possibly just use the dict, not a copy
        result = action(task.state.copy())
        match result:
            case None:
                pass
            case dict():
                task.state.update(result)
            case True:
                pass
            case False:
                self.reporter.trace(action, flags=ReportEnum.FAIL | ReportEnum.ACTION)
                raise doot.errors.DootTaskFailed("Task %s Action Failed: %s", task.name, action, task=task.spec)
            case _:
                self.reporter.trace(action, flags=ReportEnum.FAIL | ReportEnum.ACTION)
                raise doot.errors.DootTaskError("Task %s Action %s Failed: Returned an unplanned for value: %s", task.name, action, result, task=task.spec)

        action.verify_out(task.state)

        logmod.debug("------ Action Execution Complete: %s for %s", action, task.name)
        self.reporter.trace(action, flags=ReportEnum.ACTION | ReportEnum.SUCCEED)

    def _finish(self):
        """finish running tasks"""
        logging.info("Task Running Completed")
        printer.info("Final Summary: ")
        printer.info(str(self.reporter), extra={"colour":"magenta"})
