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
import doot.structs as structs
import doot.errors
from doot.enums import TaskStateEnum, ReportEnum, TaskFlags
import doot._abstract as abstract
from doot.control.runner import DootRunner
from doot.utils.signal_handler import SignalHandler

dry_run      = doot.args.on_fail(False).cmd.args.dry_run()
SLEEP_LENGTH = doot.config.on_fail(0.2, int|float).settings.general.task.sleep()

@doot.check_protocol class DootStepRunner(DootRunner):
    """ A runner with step control """
    _conf_prompt  = "::- Command? (? for help): "
    _cmd_prefix   = "_do_"
    _aliases      = { ""  : "continue",
                     "c"  : "continue",
                     "n"  : "skip",
                     "b"  : "break",
                     "l"  : "list",
                     "d"  : "down",
                     "u"  : "up",
                     "q"  : "quit",
                     "?"  : "help",
                     "I"  : "print_info",
                     "W"  : "print_warn",
                     "D"  : "print_debug",
                     }

    def __init__(self:Self, *, tracker:abstract.TaskTracker_i, reporter:abstract.Reporter_i, policy=None):
        super().__init__(tracker=tracker, reporter=reporter, policy=policy)
        self._conf_types = []
        self._override_level = "INFO"



    def _expand_tasker(self, tasker:abstract.Tasker_i) -> None:
        if self._pause(tasker):
            super()._expand_tasker(tasker)
        else:
            printer.info("::- ...")

    def _execute_task(self, task:abstract.Task_i) -> None:
        if self._pause(task):
            super()._execute_task(task)
        else:
            printer.info("::- ...")


    def _execute_action(self, count, action, task) -> None:
        if self._pause(action, step=f"{self.step}.{count}"):
            super()._execute_action(count, action, task)
        else:
            printer.info("::- ...")


    def _pause(self, target, step=None) -> bool:
        # TODO add step control to step in, cancel, or pause on completion, and jump to pdb
        if not bool(self._conf_types):
            return True

        match target:
            case _ if True in self._conf_types:
                pass
            case abstract.Tasker_i() if abstract.Tasker_i not in self._conf_types:
                return True
            case abstract.Task_i() if abstract.Task_i not in self._conf_types:
                return True
            case structs.DootActionSpec() if structs.DootActionSpec not in self._conf_types:
                return True

        printer.info("")
        printer.info( "::- Step %s: %s", (step or self.step), str(target))
        result = None
        while not isinstance(result, bool):
            response = input(self._conf_prompt)
            if hasattr(self, f"{self._cmd_prefix}{response}"):
                result = getattr(self, self._cmd_prefix + response)()
            elif response in self._aliases:
                result = getattr(self, self._cmd_prefix + self._aliases[response])()
            else:
                result = self._do_default()

        return result

    def _do_default(self, *args):
        printer.info("::- Default")
        return None

    def _do_continue(self, *args):
        printer.info("::- Continue")
        return True

    def _do_skip(self, *args):
        printer.info("::- Skipping")
        return False

    def _do_help(self, *args):
        printer.info("::- Help")
        printer.info("::-- Available Commands: %s", " ".join([x.replace(self._cmd_prefix, "") for x in dir(self) if self._cmd_prefix in x]))

        printer.info("")
        printer.info("::-- Aliases:")
        for x,y in self._aliases.items():
            if x == "":
                continue
            printer.info("::-- %s : %s", x, y)

        printer.info("")
        printer.info("::-- Pausing on: %s", self._conf_types)

        return None

    def _do_quit(self, *args):
        printer.info("::- Quitting Doot")
        self.tracker.clear_queue()
        return False

    def _do_list(self, *args):
        printer.info("::- Listing Trace:")
        for x in self.tracker.execution_path[:-1]:
            printer.info("::-- %s", x)

        printer.info("::-- Current: %s", self.tracker.execution_path[-1])

        return None

    def _do_break(self, *args):
        printer.info("::- Break")
        raise doot.errors.DootTaskInterrupt("User Interrupt")

    def _do_down(self, *args):
        printer.info("::- Down")
        match self._conf_types:
            case [True]:
                self.set_confirm_type("tasker")
            case [abstract.Tasker_i]:
                self.set_confirm_type("task")
            case [abstract.Task_i]:
                self.set_confirm_type("action")
            case [structs.DootActionSpec]:
                pass

        printer.info("::- Stepping at: %s", self._conf_types)

    def _do_up(self, *args):
        printer.info("Up")
        match self._conf_types:
            case [structs.DootActionSpec]:
                self.set_confirm_type("task")
            case [abstract.Task_i]:
                self.set_confirm_type("tasker")
            case [abstract.Tasker_i]:
                self.set_confirm_type("all")
            case [True]:
                pass

        printer.info("Stepping at: %s", self._conf_types)



    def _do_print_info(self, *args):
        self._override_level = "INFO"
        printer.warning("Overring Printer to: %s", self._override_level)
        self._set_print_level(self._override_level)

    def _do_print_warn(self, *args):
        self._override_level = "WARN"
        printer.warning("Overring Printer to: %s", self._override_level)
        self._set_print_level(self._override_level)

    def _do_print_debug(self, *args):
        self._override_level = "DEBUG"
        printer.warning("Overring Printer to: %s", self._override_level)
        self._set_print_level(self._override_level)

    def _set_print_level(self, level=None):
        if level:
            super()._set_print_level(self._override_level)
        else:
            super()._set_print_level()


    def set_confirm_type(self, val):
        match val:
            case "tasker":
                self._conf_types = [abstract.Tasker_i]
            case "task":
                self._conf_types = [abstract.Task_i]
            case "action":
                self._conf_types = [structs.DootActionSpec]
            case "all":
                self._conf_types = [True]
"""


"""
