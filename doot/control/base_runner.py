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
printer = logmod.getLogger("doot._printer")
##-- end logging

from collections import defaultdict
import doot
import doot.errors
from doot.enums import ReportEnum, ActionResponseEnum as ActRE, TaskStateEnum
from doot._abstract import Job_i, Task_i, FailPolicy_p
from doot._abstract import TaskTracker_i, TaskRunner_i, Task_i, ReportLine_i, Action_p, Reporter_i
from doot.structs import DootTaskArtifact, DootActionSpec
from doot.utils.signal_handler import SignalHandler
from doot.structs import DootTaskSpec, DootActionSpec
from doot.utils.log_context import DootLogContext

dry_run                                      = doot.args.on_fail(False).cmd.args.dry_run()
head_level           : Final[str]            = doot.constants.printer.DEFAULT_HEAD_LEVEL
build_level          : Final[str]            = doot.constants.printer.DEFAULT_BUILD_LEVEL
action_level         : Final[str]            = doot.constants.printer.DEFAULT_ACTION_LEVEL
sleep_level          : Final[str]            = doot.constants.printer.DEFAULT_SLEEP_LEVEL
execute_level        : Final[str]            = doot.constants.printer.DEFAULT_EXECUTE_LEVEL
enter_level          : Final[str]            = doot.constants.printer.DEFAULT_ENTER_LEVEL
max_steps            : Final[str]            = doot.config.on_fail(100_000).settings.tasks.max_steps()
fail_prefix          : Final[str]            = doot.constants.printer.FAILURE_PREFIX

default_SLEEP_LENGTH : Fina[int|float]       = doot.config.on_fail(0.2, int|float).settings.tasks.sleep.task()
logctx               : Final[DootLogContext] = DootLogContext(printer)

class BaseRunner(TaskRunner_i):
    """ An incomplete implementation for runners to extend """

    def __init__(self:Self, *, tracker:TaskTracker_i, reporter:Reporter_i, policy=None):
        self.tracker                                          = tracker
        self.reporter                                         = reporter
        self.policy                                           = policy
        self.step                                             = 0
        self._signal_failure : None|doot.errors.DootError     = None
        self._enter_msg                                       = "---------- Task Loop Starting ----------"
        self._exit_msg                                        = "---------- Task Loop Finished ----------"

    def __enter__(self) -> Any:
        printer.info("- Validating Task Network, building remaining abstract tasks: %s", self.tracker.late_count)
        self.tracker.validate()
        printer.info(self._enter_msg, extra={"colour" : "green"})
        return

    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        # TODO handle exc_types?
        printer.setLevel("INFO")
        printer.info("")
        printer.info(self._exit_msg, extra={"colour":"green"})
        self._finish()
        return

    def _finish(self):
        """finish running tasks, summarizing results using the reporter
          separate from __exit__ to allow it to be overridden
        """
        logging.info("Task Running Completed")
        if self.step >= max_steps:
            printer.info("Runner Hit the Step Limit: %s", max_steps)

        printer.info("Final Summary: ")
        printer.info(str(self.reporter), extra={"colour":"magenta"})
        match self._signal_failure:
            case None:
                return
            case doot.errors.DootError():
                raise self._signal_failure

    def _handle_task_success(self, task:None|Task_i|DootTaskArtifact):
        """ The basic success handler. just informs the tracker of the success """
        if task:
            self.tracker.update_state(task, self.tracker.state_e.SUCCESS)
        return task

    def _handle_failure(self, task:None|Task_i, failure:Error) -> None:
        """ The basic failure handler.
          Triggers a breakpoint on DootTaskInterrupt,
          otherwise informs the tracker of the failure.

          Halts any failed or errored tasks, which propagates to any successors
          Fails any DootErrors, TrackingErrors, and non-doot errors

          the tracker handle's clearing itself and shutting down
        """
        match failure:
            case doot.errors.DootTaskInterrupt():
                breakpoint()
                pass
            case doot.errors.DootTaskFailed() as err:
                self._signal_failure = err
                printer.warning("%s %s", fail_prefix, err)
                self.tracker.update_state(err.task.name, self.tracker.state_e.HALTED)
            case doot.errors.DootTaskError() as err:
                self._signal_failure = err
                printer.warning("%s %s", fail_prefix, err)
                self.tracker.update_state(err.task.name, self.tracker.state_e.HALTED)
            case doot.errors.DootError() as err:
                self._signal_failure = err
                printer.warning("%s %s", fail_prefix, err)
                self.tracker.update_state(task, self.tracker.state_e.FAILED)
            case doot.errors.DootTaskTrackingError() as err:
                self._signal_failure = err
                printer.warning("%s %s", fail_prefix, err)
                self.tracker.update_state(task, self.tracker.state_e.FAILED)
            case _:
                self._signal_failure = doot.errors.DootError("Unknown Failure")
                printer.exception("%s Unknown failure occurred: %s", fail_prefix, failure)
                self.tracker.update_state(task, self.tracker.state_e.FAILED)

    def _sleep(self, task):
        """
          The runner's sleep method, which spaces out tasks
        """
        match task:
            case None:
                return
            case DootTaskArtifact():
                return

        with logctx(task.spec.print_levels.on_fail(sleep_level).sleep()) as p:
            sleep_len = task.spec.extra.on_fail(default_SLEEP_LENGTH, int|float).sleep()
            p.info("[Sleeping (%s)...]", sleep_len, extra={"colour":"white"})
            time.sleep(sleep_len)

    def _notify_artifact(self, art:DootTaskArtifact) -> None:
        """ A No-op for when the tracker gives an artifact """
        printer.info("---- Artifact: %s", art)
        self.reporter.add_trace(art, flags=ReportEnum.ARTIFACT)
