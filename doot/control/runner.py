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
from doot.enums import TaskStateEnum
from doot._abstract import Tasker_i, Task_i, FailPolicy_p
from doot._abstract import TaskTracker_i, TaskRunner_i, TaskBase_i, Reporter_i, Action_p
from doot.utils.signal_handler import SignalHandler


@doot.check_protocol
class DootRunner(TaskRunner_i):
    """ The simplest single threaded task runner """

    def __init__(self:Self, tracker:TaskTracker_i, reporter:Reporter_i, *, policy=None):
        super().__init__(tracker, reporter, policy=policy)

    def __call__(self, *tasks:str):
        """ tasks are initial targets to run.
          so loop on the tracker, getting the next task,
          running its actions,
          and repeating,
          until done

          if task is a tasker, it is expanded and added into the tracker
          """
        # for threaded tasks: replace expand_tasker/execute_task/execute_action with twisted?

        with SignalHandler():
            for task in iter(self.tracker):
                if task is None:
                    continue

                try:
                    match task:
                        case Tasker_i():
                            self._expand_tasker(task)
                            self.tracker.update_state(task, TaskStateEnum.SUCCESS)
                        case Task_i():
                            self._execute_task(task)
                            self.tracker.update_state(task, TaskStateEnum.SUCCESS)
                # Handle problems:
                except doot.errors.DootTaskInterrupt as err:
                    breakpoint()
                    pass
                except doot.errors.DootTaskTrackingError as err:
                    pass
                except doot.errors.DootTaskFailed as err:
                    self.tracker.update_state(task, TaskStateEnum.Failed)
                except doot.errors.DootTaskError as err:
                    pass
                except doot.errors.DootError as err:
                    self.tracker.update_state(task, TaskStateEnum.Failed)
                else:
                    printer.info("Sleeping")
                    time.sleep(0.2)


        self._finish()

    def _expand_tasker(self, tasker:Tasker_i) -> None:
        """ turn a tasker into all of its tasks, including teardowns """
        logging.debug("-- Expanding Tasker: %s", tasker.name)
        count = 0
        for task in tasker.build():
            match task:
                case Tasker_i():
                    raise doot.errors.DootTaskError("Taskers can't build taskers")
                case Task_i():
                    self.tracker.add_task(task, no_root_connection=True)
                    self.tracker.queue_task(task.name)
                case _:
                    raise doot.errors.DootTaskError("Tasker Built a Bad Value", task)
            count += 1

        logging.debug("-- Tasker %s Expansion produced: %s tasks", tasker.name, count)

    def _execute_task(self, task:Task_i) -> None:
        """ execute a single task's actions """
        logging.debug("---- Executing Task: %s", task.name)
        # TODO <-- in the future, where DB checks for staleness, thread safety, etc will occur

        for action in task.actions:
            match action:
                case Action_p():
                    self._execute_action(action, task)
                case _:
                    raise doot.errors.DootTaskError("Task produced a bad action", action)

        # Get Any resulting tasks
        count = 0
        for new_task in task.maybe_more_tasks():
            match new_task:
                case Task_i():
                    self.tracker.add_task(new_task, no_root_connection=True)
                    count += 1
                case _:
                    raise doot.errors.DootTaskError("Task provided a bad additional task", new_task)


        logging.debug("---- Task Execution Completed: %s, adding %s additional tasks", task.name, count)

    def _execute_action(self, action, task) -> None:
        """ Run the given action of a specific task  """
        logging.debug("------ Executing Action: %s for %s", action, task.name)
        result = action(task.state.copy())
        match result:
            case None:
                pass
            case bool():
                pass
            case dict():
                task.state.update(result)
        logging.debug("------ Action Execution Complete: %s for %s", action, task.name)

    def _finish(self):
        """finish running tasks"""
        printer.info("Task Running Completed")
