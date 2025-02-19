#!/usr/bin/env python3
"""

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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.debugging import SignalHandler
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.enums import ActionResponse_e as ActRE
from doot.enums import Report_f, TaskStatus_e
from doot.structs import ActionSpec, TaskArtifact, TaskSpec

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
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

##--|
from doot._abstract import Task_p
# isort: on
# ##-- end types

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

dry_run              : Final[bool]           = doot.args.on_fail(False).cmd.args.dry_run()
max_steps            : Final[str]            = doot.config.on_fail(100_000).startup.max_steps()
fail_prefix          : Final[str]            = doot.constants.printer.fail_prefix
loop_entry_msg       : Final[str]            = doot.constants.printer.loop_entry
loop_exit_msg        : Final[str]            = doot.constants.printer.loop_exit

default_SLEEP_LENGTH : Final[int|float]       = doot.config.on_fail(0.2, int|float).startup.sleep.task()

class _RunnerCtx_m:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._enter_msg = loop_entry_msg
        self._exit_msg  = loop_exit_msg
        self._signal_failure : Maybe[doot.errors.DootError]   = None

    def __enter__(self) -> Self:
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

class _RunnerHandlers_m:

    def _handle_task_success(self, task:Maybe[Task_p|TaskArtifact]):
        """ The basic success handler. just informs the tracker of the success """
        success_l.debug("(Task): %s", task)
        match task:
            case None:
                pass
            case _:
                self.tracker.set_status(task, TaskStatus_e.SUCCESS)
        return task

    def _handle_failure(self, task:Task_p, failure:Error) -> None:
        """ The basic failure handler.
          Triggers a breakpoint on Interrupt,
          otherwise informs the tracker of the failure.

          Halts any failed or errored tasks, which propagates to any successors
          Fails any DootErrors, TrackingErrors, and non-doot errors

          the tracker handle's clearing itself and shutting down
        """
        match failure:
            case doot.errors.Interrupt():
                breakpoint()
                pass
            case doot.errors.TaskFailed() as err:
                self._signal_failure = err
                fail_l.warning("%s Halting: %s", fail_prefix, err)
                self.tracker.set_status(err.task, TaskStatus_e.HALTED)
            case doot.errors.TaskError() as err:
                self._signal_failure = err
                self.tracker.set_status(err.task, TaskStatus_e.FAILED)
                raise err
            case doot.errors.TrackingError() as err:
                self._signal_failure = err
                self.tracker.set_status(task, TaskStatus_e.FAILED)
                raise err
            case doot.errors.DootError() as err:
                self._signal_failure = err
                self.tracker.set_status(task, TaskStatus_e.FAILED)
                raise err
            case _:
                self._signal_failure = doot.errors.DootError("Unknown Failure")
                fail_l.exception("%s Unknown failure occurred: %s", fail_prefix, failure)
                self.tracker.set_status(task, TaskStatus_e.FAILED)
                raise err

    def _notify_artifact(self, art:TaskArtifact) -> None:
        """ A No-op for when the tracker gives an artifact """
        artifact_l.info("---- Artifact: %s", art)
        self.reporter.add_trace(art, flags=Report_f.ARTIFACT)
        raise doot.errors.StateError("Artifact resolutely does not exist", art)

class _RunnerSleep_m:
    """ An incomplete implementation for runners to extend """

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
