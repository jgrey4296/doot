#!/usr/bin/env python3
"""

"""
# ruff: noqa: PLR1711
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
import weakref
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto, Mixin
from jgdv.debugging import SignalHandler

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot._abstract as abstract
import doot.errors
from doot import structs
from doot.control.runner import DootRunner
from doot.enums import TaskMeta_e, TaskStatus_e

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
from doot._abstract import TaskRunner_i
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

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)

##-- end logging

dry_run        : final[bool] = doot.args.on_fail(False).cmd.args.dry_run()
SLEEP_LENGTH   : Final[int]  = doot.config.on_fail(0.2, int|float).startup.sleep.task()
MAX_LOG_ACTIVE : Final[int]  = 100
CMDS           : Final[dict] = {
  ""           : "continue",
  "c"          : "continue",
  "n"          : "skip",
  "b"          : "break",
  "l"          : "list",
  "d"          : "down",
  "u"          : "up",
  "q"          : "quit",
  "?"          : "help",
  "I"          : "print_info",
  "W"          : "print_warn",
  "D"          : "print_debug",
  "s"          : "print_state",
 }

##--|

class _Instructions_m:

    def _do_default(self, *args):
        doot.report.trace("::- Default")
        return None

    def _do_continue(self, *args):
        doot.report.trace("::- Continue")
        return True

    def _do_skip(self, *args):
        doot.report.trace("::- Skipping")
        return False

    def _do_help(self, *args):
        doot.report.trace("::- Help")
        doot.report.trace("::-- Available Commands: %s", " ".join([x.replace(self._cmd_prefix, "") for x in dir(self) if self._cmd_prefix in x]))

        doot.report.trace("")
        doot.report.trace("::-- Aliases:")
        for x,y in self._aliases.items():
            if x == "":
                continue
            doot.report.trace("::-- %s : %s", x, y)

        doot.report.gap()
        doot.report.trace("::-- Pausing on: %s", self._conf_types)

        return None

    def _do_quit(self, *args):
        doot.report.trace("::- Quitting Doot")
        self.tracker.clear_queue()
        if len(self.tracker.active_set) < MAX_LOG_ACTIVE:
            doot.report.trace("Tracker Queue: %s", self.tracker.active_set)
        else:
            doot.report.trace("Tracker Queue: %s", len(self.tracker_set))
        self._has_quit = True
        return False

    def _do_list(self, *args):
        doot.report.trace("::- Listing Trace:")
        for x in self.tracker.execution_path[:-1]:
            doot.report.trace("::-- %s", x)

        doot.report.trace("::-- Current: %s", self.tracker.execution_path[-1])

        return None

    def _do_break(self, *args):
        doot.report.trace("::- Break")
        breakpoint()
        pass

    def _do_down(self, *args):
        doot.report.trace("::- Down")
        match self._conf_types:
            case [True]:
                self.set_confirm_type("job")
            case [abstract.Job_i]:
                self.set_confirm_type("task")
            case [abstract.Task_i]:
                self.set_confirm_type("action")
            case [structs.ActionSpec]:
                self.set_confirm_type("all")
                pass

        doot.report.trace("::- Stepping at: %s", self._conf_types)

    def _do_up(self, *args):
        doot.report.trace("Up")
        match self._conf_types:
            case [structs.ActionSpec]:
                self.set_confirm_type("task")
            case [abstract.Task_i]:
                self.set_confirm_type("job")
            case [abstract.Job_i]:
                self.set_confirm_type("all")
            case [True]:
                pass

        doot.report.trace("Stepping at: %s", self._conf_types)

    def _do_print_info(self, *args):
        self._override_level = "INFO"
        doot.report.warn("Overring Printer to: %s", self._override_level)
        self._set_print_level(self._override_level)

    def _do_print_warn(self, *args):
        self._override_level = "WARNING"
        doot.report.warn("Overring Printer to: %s", self._override_level)
        self._set_print_level(self._override_level)

    def _do_print_debug(self, *args):
        self._override_level = "DEBUG"
        doot.report.warn("Overring Printer to: %s", self._override_level)
        self._set_print_level(self._override_level)

    def _do_print_state(self, *args):
        doot.report.trace("Current State:")
        doot.report.trace("%20s : %s", "CLI Args", dict(doot.args))
        for arg in args:
            match arg:
                case structs.ActionSpec():
                    doot.report.trace("%20s : %s", "Action", str(arg.do))
                    doot.report.trace("%20s : %s", "Action Spec kwargs", dict(arg.kwargs))
                case abstract.Task_i():
                    doot.report.trace("%20s : %s", "Task Name", str(arg.name))
                    doot.report.trace("%20s : %s", "Task State", arg.state)
                case abstract.Job_i():
                    doot.report.trace("%20s : %s", "Job Args", arg.args)

class _Stepper_m:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conf_types     = []
        self._override_level = "INFO"
        self._has_quit       = False

    def _expand_job(self, job:abstract.Job_i) -> None:
        if self._pause(job):
            super()._expand_job(job)
        else:
            doot.report.trace("::- ...")

    def _execute_task(self, task:abstract.Task_i) -> None:
        if self._pause(task):
            super()._execute_task(task)
        else:
            doot.report.trace("::- ...")

    def _execute_action(self, count, action, task) -> None:
        if self._pause(action, task, step=f"{self.step}.{count}"):
            return super()._execute_action(count, action, task)
        else:
            doot.report.trace("::- ...")

    def _pause(self, *args, step=None) -> bool:
        if self._has_quit:
            return False

        if not bool(self._conf_types):
            return True

        target = args[0]
        match target:
            case _ if True in self._conf_types:
                pass
            case abstract.Job_i() if abstract.Job_i not in self._conf_types:
                return True
            case abstract.Task_i() if abstract.Task_i not in self._conf_types:
                return True
            case structs.ActionSpec() if structs.ActionSpec not in self._conf_types:
                return True

        doot.report.trace("")
        doot.report.trace( "::- Step %s: %s", (step or self.step), str(target))
        result = None
        while not isinstance(result, bool):
            response = input(self._conf_prompt)
            if hasattr(self, f"{self._cmd_prefix}{response}"):
                result = getattr(self, self._cmd_prefix + response)(*args)
            elif response in self._aliases:
                result = getattr(self, self._cmd_prefix + self._aliases[response])(*args)
            else:
                result = self._do_default(*args)

        return result

    def _set_print_level(self, level=None):
        if level:
            super()._set_print_level(self._override_level)
        else:
            super()._set_print_level()

    def set_confirm_type(self, val):
        """ Sets the runners `breakpoints` """
        match val:
            case "job":
                self._conf_types = [abstract.Job_i]
            case "task":
                self._conf_types = [abstract.Task_i]
            case "action":
                self._conf_types = [structs.ActionSpec]
            case "all":
                self._conf_types = [True]


##--|
@Proto(TaskRunner_i)
@Mixin(_Instructions_m, _Stepper_m)
class DootStepRunner(DootRunner):
    """ extends the default runner with step control """
    _conf_prompt                      = "::- Command? (? for help): "
    _cmd_prefix                       = "_do_"
    _aliases      : ClassVar[dict]    = CMDS.copy()
