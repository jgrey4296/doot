#!/usr/bin/env python3
"""

"""
# mypy: disable-error-code="attr-defined"
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
from collections import defaultdict
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.debugging import SignalHandler
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.workflow._interface import ActionResponse_e as ActRE
from doot.workflow._interface import TaskStatus_e
from doot.workflow import ActionSpec, TaskSpec, TaskArtifact

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
from doot.workflow._interface import Task_p

if TYPE_CHECKING:
    from jgdv import Maybe, Traceback
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|
# isort: on
# ##-- end types

##-- logging
logging    = logmod.getLogger(__name__)
##-- end logging

dry_run              : Final[bool]            = doot.args.on_fail(False).cmd.args.dry_run()  # noqa: FBT003
max_steps            : Final[int]             = doot.config.on_fail(100_000).commands.run.max_steps()
fail_prefix          : Final[str]             = doot.constants.printer.fail_prefix
loop_entry_msg       : Final[str]             = doot.constants.printer.loop_entry
loop_exit_msg        : Final[str]             = doot.constants.printer.loop_exit

DEFAULT_SLEEP_LENGTH : Final[int|float]       = doot.config.on_fail(0.2, int|float).commands.run.sleep.task()
##--|

class _RunnerCtx_m:
    """ Mixin for a runner that adds ctx manager functionality """

    _signal_failure : Maybe[doot.errors.DootError]

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
        self._enter_msg      = loop_entry_msg
        self._exit_msg       = loop_exit_msg
        self._signal_failure = None

    def __enter__(self) -> Self:
        logging.info("Entering Runner Control")
        doot.report.trace("Building Task Network...")
        doot.report.gap()
        self.tracker.build_network()
        doot.report.trace("Task Network Built.")
        doot.report.detail("Network Composition: %s Nodes, %s Edges, %s Edges from Root.",
                           len(self.tracker.network.nodes),
                           len(self.tracker.network.edges),
                           len(self.tracker.network.pred[self.tracker._root_node]))
        doot.report.trace("Validating Task Network...")
        doot.report.gap()
        self.tracker.validate_network()
        doot.report.trace("Validation Complete.")
        doot.report.line(self._enter_msg)
        doot.report.root()
        return self

    def __exit__(self, exc_type:type[Exception], exc_value:Exception, exc_traceback:Traceback) -> Literal[False]:
        logging.info("Exiting Runner Control")
        # TODO handle exc_types?
        self._finish()
        return False

    def _finish(self) -> None:
        """finish running tasks, summarizing results using the reporter
          separate from __exit__ to allow it to be overridden
        """
        logging.info("Running Completed")
        if self.step >= max_steps:
            doot.report.warn("Runner Hit the Step Limit: %s", max_steps)

        doot.report.finished().gap().line(self._exit_msg)
        match self._signal_failure:
            case None:
                return
            case doot.errors.DootError():
                raise self._signal_failure

class _RunnerHandlers_m:
    """ Mixin for runners with default handlers """

    _signal_failure : Maybe[doot.errors.DootError]

    def handle_task_success[T:Maybe[Task_p|TaskArtifact]](self, task:T) -> T:
        """ The basic success handler. just informs the tracker of the success """
        match task:
            case None:
                pass
            case TaskArtifact() as art:
                doot.report.result([art.path], info="Success")
            case Task_p():
                doot.report.result([task.name[:]], info="Success")
                self.tracker.set_status(task, TaskStatus_e.SUCCESS)
        return task

    def handle_failure(self, failure:Exception) -> None:
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
                doot.report.warn("%s Halting: %s", fail_prefix, err)
                self.tracker.set_status(err.task, TaskStatus_e.HALTED)
            case doot.errors.TaskError() as err:
                doot.report.fail()
                self._signal_failure = err
                self.tracker.set_status(err.task, TaskStatus_e.FAILED)
                raise err
            case doot.errors.TrackingError() as err:
                doot.report.fail()
                self._signal_failure = err
                raise err
            case doot.errors.DootError() as err:
                doot.report.fail()
                self._signal_failure = err
                raise err
            case err:
                doot.report.fail()
                self._signal_failure = doot.errors.DootError("Unknown Failure")
                doot.report.error("%s Unknown failure occurred: %s", fail_prefix, failure)
                raise err

    def notify_artifact(self, art:TaskArtifact) -> None:
        """ A No-op for when the tracker gives an artifact """
        doot.report.result(["Artifact: %s", art])
        raise doot.errors.StateError("Artifact resolutely does not exist", art)

    def sleep_after(self, task:Maybe[Task_p|TaskArtifact]) -> None:
        """
          The runner's sleep method, which spaces out tasks
        """
        match task:
            case None:
                return
            case TaskArtifact():
                return

        sleep_len = task.spec.extra.on_fail(DEFAULT_SLEEP_LENGTH, int|float).sleep()
        doot.report.detail("[Sleeping (%s)...]", sleep_len, extra={"colour":"white"})
        time.sleep(sleep_len)
