#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
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
from collections import defaultdict
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import more_itertools as mitz

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import (Action_p, FailPolicy_p, Job_i, Reporter_p, Task_i,
                            TaskRunner_i, TaskTracker_i)
from doot.enums import ActionResponse_e as ActRE
from doot.enums import Report_f, TaskStatus_e
from doot.structs import ActionSpec, TaskArtifact, TaskSpec
from doot.utils.signal_handler import SignalHandler

# ##-- end 1st party imports

##-- logging
logging    = logmod.getLogger(__name__)
printer    = doot.subprinter()
setup_l    = doot.subprinter("setup")
taskloop_l = doot.subprinter("task_loop")
report_l   = doot.subprinter("report")
success_l  = doot.subprinter("success")
fail_l     = doot.subprinter("fail")
sleep_l    = doot.subprinter("sleep")
artifact_l = doot.subprinter("artifact")
##-- end logging

dry_run                                      = doot.args.on_fail(False).cmd.args.dry_run()
max_steps            : Final[str]            = doot.config.on_fail(100_000).settings.tasks.max_steps()
fail_prefix          : Final[str]            = doot.constants.printer.fail_prefix
loop_entry_msg       : Final[str]            = doot.constants.printer.loop_entry
loop_exit_msg        : Final[str]            = doot.constants.printer.loop_exit

default_SLEEP_LENGTH : Fina[int|float]       = doot.config.on_fail(0.2, int|float).settings.tasks.sleep.task()

class BaseRunner(TaskRunner_i):
    """ An incomplete implementation for runners to extend """

    def __init__(self:Self, *, tracker:TaskTracker_i, reporter:Reporter_p):
        self.tracker                                          = tracker
        self.reporter                                         = reporter
        self.step                                             = 0
        self._signal_failure : None|doot.errors.DootError     = None
        self._enter_msg                                       = loop_entry_msg
        self._exit_msg                                        = loop_exit_msg

    def __enter__(self) -> Any:
        setup_l.info("Building Task Network...")
        self.tracker.build_network()
        setup_l.info("Task Network Built. %s Nodes, %s Edges, %s Edges from Root.",
                     len(self.tracker.network.nodes), len(self.tracker.network.edges), len(self.tracker.network.pred[self.tracker._root_node]))
        setup_l.info("Validating Task Network...")
        self.tracker.validate_network()
        setup_l.info("Validation Complete")
        taskloop_l.info(self._enter_msg, extra={"colour" : "green"})
        return

    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        logging.info("---- Exiting Runner Control")
        # TODO handle exc_types?
        printer.setLevel("INFO")
        taskloop_l.info("")
        taskloop_l.info(self._exit_msg, extra={"colour":"green"})
        self._finish()
        return

    def _finish(self):
        """finish running tasks, summarizing results using the reporter
          separate from __exit__ to allow it to be overridden
        """
        logging.info("---- Running Completed")
        if self.step >= max_steps:
            report_l.warning("Runner Hit the Step Limit: %s", max_steps)

        report_l.info("Final Summary: ")
        report_l.info(str(self.reporter), extra={"colour":"magenta"})
        match self._signal_failure:
            case None:
                return
            case doot.errors.DootError():
                raise self._signal_failure

    def _handle_task_success(self, task:None|Task_i|TaskArtifact):
        """ The basic success handler. just informs the tracker of the success """
        success_l.debug("(Task): %s", task)
        match task:
            case None:
                pass
            case _:
                self.tracker.set_status(task, TaskStatus_e.SUCCESS)
        return task

    def _handle_failure(self, task:Task_i, failure:Error) -> None:
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
                fail_l.warning("%s %s", fail_prefix, err)
                self.tracker.set_status(err.task, TaskStatus_e.HALTED)
            case doot.errors.DootTaskError() as err:
                self._signal_failure = err
                fail_l.warning("%s %s", fail_prefix, err)
                self.tracker.set_status(err.task, TaskStatus_e.FAILED)
            case doot.errors.DootError() as err:
                self._signal_failure = err
                fail_l.warning("%s %s", fail_prefix, err)
                self.tracker.set_status(task, TaskStatus_e.FAILED)
            case doot.errors.DootTaskTrackingError() as err:
                self._signal_failure = err
                fail_l.warning("%s %s", fail_prefix, err)
                self.tracker.set_status(task, TaskStatus_e.FAILED)
            case _:
                self._signal_failure = doot.errors.DootError("Unknown Failure")
                fail_l.exception("%s Unknown failure occurred: %s", fail_prefix, failure)
                self.tracker.set_status(task, TaskStatus_e.FAILED)

    def _sleep(self, task):
        """
          The runner's sleep method, which spaces out tasks
        """
        match task:
            case None:
                return
            case TaskArtifact():
                return

        sleep_len = task.spec.extra.on_fail(default_SLEEP_LENGTH, int|float).sleep()
        sleep_l.debug("[Sleeping (%s)...]", sleep_len, extra={"colour":"white"})
        time.sleep(sleep_len)

    def _notify_artifact(self, art:TaskArtifact) -> None:
        """ A No-op for when the tracker gives an artifact """
        artifact_l.info("---- Artifact: %s : %s", art, art.expand())
        self.reporter.add_trace(art, flags=Report_f.ARTIFACT)
