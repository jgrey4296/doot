#!/usr/bin/env python3
"""


See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

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
from doot.control.runner import DootRunner
from doot.utils.signal_handler import SignalHandler
from doot.structs import DootTaskSpec, DootActionSpec

dry_run      = doot.args.on_fail(False).cmd.args.dry_run()
SLEEP_LENGTH = doot.config.on_fail(0.2, int|float).settings.general.task.sleep()

@doot.check_protocol
class DootStepRunner(DootRunner):
    """ A runner with step control """
    _conf_query   = "Confirm? yes:RET, no:* "
    _conf_match   = ""

    def __init__(self:Self, *, tracker:TaskTracker_i, reporter:Reporter_i, policy=None):
        super().__init__(tracker=tracker, reporter=reporter, policy=policy)
        self._conf_types = []

    def set_confirm_type(self, val):
        match val:
            case "tasker":
                self._conf_types.append(Tasker_i)
            case "task":
                self._conf_types.append(Task_i)
            case "action":
                self._conf_types.append(True)
            case "all":
                self._conf_types = [Tasker_i, Task_i, True]


    def _confirm_p(self, target, step=None) -> bool:
        # TODO add step control to step in, cancel, or pause on completion, and jump to pdb
        if not bool(self._conf_types):
            return True

        match target:
            case Tasker_i() if Tasker_i in self._conf_types:
                printer.info( "-----? About To Peform Tasker, Step %s: %s", (step or self.step), target.name)
                return input(self._conf_query) == self._conf_match
            case Tasker_i():
                return True
            case Task_i() if Task_i in self._conf_types:
                printer.info( "-----? About To Peform Task, Step %s: %s", (step or self.step), target.name)
                return input(self._conf_query) == self._conf_match
            case Task_i():
                return True
            case _ if True in self._conf_types:
                printer.info( "-----? About To Peform Action, Step %s: %s", (step or self.step), str(target))
                return input(self._conf_query) == self._conf_match

        return True

    def _expand_tasker(self, tasker:Tasker_i) -> None:
        if self._confirm_p(tasker):
            super()._expand_tasker(tasker)
        else:
            printer.info("..")

    def _execute_task(self, task:Task_i) -> None:
        if self._confirm_p(task):
            super()._execute_task(task)
        else:
            printer.info("...")
            print.info("")


    def _execute_action(self, count, action, task) -> None:
        if self._confirm_p(action, step=f"{self.step}.{count}"):
            super()._execute_action(count, action, task)
        else:
            printer.info("..")


"""


"""
