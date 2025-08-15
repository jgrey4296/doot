 #!/usr/bin/env python3
"""

"""
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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto
from jgdv.debugging.timing import TimeCtx
from jgdv.structs.strang import CodeReference
from jgdv.util.plugins.selector import plugin_selector

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.control.runner.step_runner import DootStepRunner
from doot.workflow.check_locs import CheckLocsTask

# ##-- end 1st party imports

# ##-| Local
from ._base import BaseCommand
from ._interface import Command_p

# # End of Imports.

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
    from typing import Never, Self, Literal, ContextManager
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from jgdv.structs.chainguard import ChainGuard
    from doot.control.runner._inteface import WorkflowRunner_p
    from doot.control.tracker._interface import WorkflowTracker_p

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# TODO make a decorator to register these onto the cmd
tracker_target     : Final       = doot.config.on_fail("default", str).settings.commands.run.tracker()
runner_target      : Final       = doot.config.on_fail("default", str).settings.commands.run.runner()
reporter_target    : Final       = doot.config.on_fail("default", str).settings.commands.run.reporter()
interrupt_handler  : Final       = doot.config.on_fail("jgdv.debugging:SignalHandler", bool|str).settings.commands.run.interrupt()
check_locs         : Final       = doot.config.on_fail(False).settings.commands.run.location_check.active()  # noqa: FBT003

CONFIRM            : Final[str]  = "Y"
##--|

@Proto(Command_p)
class RunCmd(BaseCommand):
    _name  = "run"
    _help  = tuple(["Will perform the tasks/jobs targeted.",
                   "Can be parameterized in a commands.run block with:",
                   "tracker(str), runner(str)",
                   ])

    @override
    def param_specs(self) -> list:
        return [
            *super().param_specs(),
            self.build_param(name="--interrupt", default=False, type=bool, desc="Activate interrupt handler"),
            self.build_param(name="--step",      default=False, type=bool, desc="Interrupt between workflow step"),
            self.build_param(name="--dry-run",   default=False, type=bool, desc="Don't perform actions"),
            self.build_param(name="--confirm",   default=False, type=bool, desc="Confirm the expected workflow plan"),
            ]

    def __call__(self, *, idx:int, tasks:ChainGuard, plugins:ChainGuard):
        tracker    : WorkflowTracker_p
        runner     : WorkflowRunner_p
        interrupt  : Maybe[bool|type[ContextManager]|ContextManager]
        ##--|
        doot.load_reporter(target=reporter_target)

        doot.report.active_level(logmod.INFO)
        doot.report.gen.gap()
        doot.report.gen.line(f"Starting Run Cmd ({idx})", char="=")
        tracker, runner = self._create_tracker_and_runner(idx, plugins)
        interrupt       = self._choose_interrupt_handler(idx)

        self._register_specs(idx, tracker, tasks)
        self._queue_tasks(idx, tracker)

        logging.info("---- Starting Runner")
        with (TimeCtx(logger=logging,
                      level=21) as timer,
              runner,
              ):
            if not self._confirm_plan(idx, runner):
                return
            runner(handler=interrupt)

        logging.info("---- Runner took: %s seconds", timer.total_s)

    def _create_tracker_and_runner(self, idx:int, plugins:ChainGuard) -> tuple[WorkflowTracker_p, WorkflowRunner_p]:
        # Note the final parens to construct:
        trackers  = plugins.on_fail([], list).tracker()
        runners   = plugins.on_fail([], list).runner()

        match plugin_selector(trackers, target=tracker_target):
            case type() as x:
                tracker = x()
            case x:
                raise TypeError(type(x))

        match plugin_selector(runners, target=runner_target):
            case _ if doot.args.on_fail(False).cmd[self.name][idx].args.step():  # noqa: FBT003
                runner = DootStepRunner(tracker=tracker)
            case type() as x:
                runner = x(tracker=tracker)
            case x:
                raise TypeError(type(x))

        return tracker, runner

    def _choose_interrupt_handler(self, idx:int) -> Maybe[bool|type|ContextManager]:
        match interrupt_handler:
            case _ if not doot.args.on_fail(False).cmd[self.name][idx].args.interrupt():  # noqa: FBT003
                return None
            case None:
                return None
            case True:
                doot.report.gen.trace("Setting default interrupt handler")
                return True
            case str():
                doot.report.gen.trace("Loading custom interrupt handler")
                ref = CodeReference(interrupt_handler)
                return ref(raise_error=True)
            case _:
                return None


    def _register_specs(self, idx:int, tracker:WorkflowTracker_p, tasks:ChainGuard) -> None:
        doot.report.gen.trace("Registering Task Specs: %s", len(tasks))
        for task in tasks.values():
            tracker.register(task)

        match CheckLocsTask():
            case x if bool(x.spec.actions) and check_locs:
                tracker.queue(CheckLocsTask(), from_user=True)
            case _:
                pass

    def _queue_tasks(self, idx:int, tracker:WorkflowTracker_p) -> None:
        doot.report.gen.trace("Queuing Initial Tasks...")
        doot.report.gen.gap()

        for sub, calls in doot.args.on_fail({}).subs().items():
            for i,_ in enumerate(calls, 1):
                try:
                    tracker.queue(sub, from_user=i)
                except doot.errors.TrackingError as err:
                    logging.exception("Failed to Queue Target: %s : %s", sub, err.args, exc_info=None)
                    return
        else:
            doot.report.gen.trace("%s Tasks Queued", len(tracker.active))

    def _confirm_plan(self, idx:int, runner:WorkflowRunner_p) -> bool:
        """ Generate and Confirm the plan from the tracker"""
        if not doot.args.on_fail(False).cmd[self.name][idx].args.confirm():  # noqa: FBT003
            return True

        tracker  = runner.tracker
        plan     = tracker.generate_plan()
        for i,(depth,node,_desc) in enumerate(plan):
            doot.report.gen.trace("(D:%s) Step %-4s: %s", depth, i, node)
        else:
            match input("Confirm Execution Plan (Y/*): "):
                case str() as x if x == CONFIRM:
                    return True
                case _:
                    doot.report.gen.trace("Cancelling")
                    return False

    def _accept_subcmds(self) -> Literal[True]:
        return True
