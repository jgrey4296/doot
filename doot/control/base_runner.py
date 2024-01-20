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
import doot.constants
import doot.errors
from doot.enums import ReportEnum, ActionResponseEnum as ActRE, TaskStateEnum
from doot._abstract import Job_i, Task_i, FailPolicy_p
from doot._abstract import TaskTracker_i, TaskRunner_i, TaskBase_i, ReportLine_i, Action_p, Reporter_i
from doot.structs import DootTaskArtifact
from doot.utils.signal_handler import SignalHandler
from doot.structs import DootTaskSpec, DootActionSpec
from doot.utils.log_context import DootLogContext

dry_run                                      = doot.args.on_fail(False).cmd.args.dry_run()
head_level           : Final[str]            = doot.constants.DEFAULT_HEAD_LEVEL
build_level          : Final[str]            = doot.constants.DEFAULT_BUILD_LEVEL
action_level         : Final[str]            = doot.constants.DEFAULT_ACTION_LEVEL
sleep_level          : Final[str]            = doot.constants.DEFAULT_SLEEP_LEVEL
execute_level        : Final[str]            = doot.constants.DEFAULT_EXECUTE_LEVEL
max_steps            : Final[str]            = doot.config.on_fail(100_000).settings.general.max_steps()

default_SLEEP_LENGTH : Fina[int|float]       = doot.config.on_fail(0.2, int|float).settings.tasks.sleep.task()
logctx               : Final[DootLogContext] = DootLogContext(printer)

class BaseRunner(TaskRunner_i):
    """ An incomplete implementation for runners to extend """

    def __init__(self:Self, *, tracker:TaskTracker_i, reporter:Reporter_i, policy=None):
        self.tracker              = tracker
        self.reporter             = reporter
        self.policy               = policy
        self.step                 = 0
        self._enter_msg = "---------- Task Loop Starting ----------"
        self._exit_msg  = "---------- Task Loop Finished ----------"

    def __enter__(self) -> Any:
        printer.info("- Validating Task Network, building remaining abstract tasks")
        self.tracker.validate()
        printer.info(self._enter_msg, extra={"colour" : "green"})
        return

    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        printer.setLevel("INFO")
        printer.info("")
        printer.info(self._exit_msg, extra={"colour":"green"})
        self._finish()
        return

    def _finish(self):
        """finish running tasks, summarizing results
          separate from __exit__ to allow it to be overridden
        """
        logging.info("Task Running Completed")
        if self.step >= max_steps:
            printer.info("Runner Hit the Step Limit: %s", max_steps)

        printer.info("Final Summary: ")
        printer.info(str(self.reporter), extra={"colour":"magenta"})

    def _handle_task_success(self, task):
        if task:
            self.tracker.update_state(task, self.tracker.state_e.SUCCESS)
        return task

    def _handle_failure(self, failure):
        match failure:
            case doot.errors.DootTaskInterrupt():
                breakpoint()
                return failure
            case doot.errors.DootTaskTrackingError() as err:
                return err.task
            case doot.errors.DootTaskFailed() as err:
                printer.warning("Task Failed: %s : %s", err.task.name, err)
                self.tracker.update_state(err.task, self.tracker.state_e.FAILED)
                return err.task
            case doot.errors.DootTaskError() as err:
                name = err.task.name if err.task is not None else "unknown"
                printer.warning("Task Error : %s : %s", name, err)
                self.tracker.update_state(err.task, self.tracker.state_e.FAILED)
                return err.task
            case doot.errors.DootError() as err:
                printer.warning("Doot Error : %s", err)
                return failure
            case _:
                return failure

    def _sleep(self, task):
        if task is None:
            return

        with logctx(task.spec.print_levels.on_fail(sleep_level).sleep()) as p:
            sleep_len = task.spec.extra.on_fail(default_SLEEP_LENGTH, int|float).sleep()
            p.info("[Sleeping (%s)...]", sleep_len, extra={"colour":"white"})
            time.sleep(sleep_len)
            self.step += 1

    def _notify_artifact(self, art:DootTaskArtifact) -> None:
        printer.info("---- Artifact: %s", art)
        self.reporter.trace(art, flags=ReportEnum.ARTIFACT)
