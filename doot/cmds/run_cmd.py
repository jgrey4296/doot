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
from jgdv.structs.strang import CodeReference
from jgdv.debugging.timeblock_ctx import TimeBlock_ctx
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot._abstract import Command_p
from doot.cmds.core.cmd import BaseCommand
from doot.task.check_locs import CheckLocsTask
from jgdv.util.plugins.selector import plugin_selector


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
    from jgdv.structs.chainguard import ChainGuard
    from doot._abstract import TaskRunner_i, TaskTracker_i

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# TODO make a decorator to register these onto the cmd
tracker_target           = doot.config.on_fail("default", str).settings.commands.run.tracker()
runner_target            = doot.config.on_fail("default", str).settings.commands.run.runner()
interrupt_handler        = doot.config.on_fail("jgdv.debugging:SignalHandler", bool|str).settings.commands.run.interrupt()
##--|
@Proto(Command_p)
class RunCmd(BaseCommand):
    _name                        = "run"
    _help : ClassVar[tuple[str]] = tuple(["Will perform the tasks/jobs targeted.",
                                          "Can be parameterized in a commands.run block with:",
                                          "tracker(str), runner(str)",
                                          ])

    @property
    def param_specs(self) -> list:
        return [
            *super().param_specs,
            self.build_param(name="--interrupt",               default=False, type=bool),
            self.build_param(name="--step",                     default=False, type=bool),
            self.build_param(name="--dry-run",                  default=False, type=bool),
            self.build_param(name="--confirm",                  default=False, type=bool),
            self.build_param(name="<1>target", type=list[str], default=[]),
            ]

    def __call__(self, tasks:ChainGuard, plugins:ChainGuard):
        doot.report.active_level(logmod.INFO)
        doot.report.set_state("cmd")
        doot.report.gap()
        doot.report.line("Starting Run Cmd", char="=")
        tracker, runner = self._create_tracker_and_runner(plugins)
        interrupt       = self._choose_interrupt_handler()

        self._register_specs(tracker, tasks)
        self._queue_tasks(tracker)

        with (TimeBlock_ctx(logger=logging,
                            enter="--- Runner Entry",
                            exit="--- Runner Exit",
                            level=20),
              runner,
              ):
            if not self._confirm_plan(runner):
                return
            runner(handler=interrupt)

    def _create_tracker_and_runner(self, plugins) -> tuple[TaskTracker_i, TaskRunner_i]:
        # Note the final parens to construct:
        trackers  = plugins.on_fail([], list).tracker()
        runners   = plugins.on_fail([], list).runner()

        match plugin_selector(trackers, target=tracker_target):
            case type() as x:
                tracker = x()
            case x:
                raise TypeError(type(x))

        match plugin_selector(runners, target=runner_target):
            case type() as x:
                runner = x(tracker=tracker)
            case x:
                raise TypeError(type(x))

        return tracker, runner

    def _register_specs(self, tracker, tasks) -> None:
        doot.report.trace("Registering Task Specs: %s", len(tasks))
        for task in tasks.values():
            tracker.register_spec(task)

        match CheckLocsTask():
            case x if bool(x.spec.actions):
                tracker.queue_entry(CheckLocsTask(), from_user=True)
            case _:
                pass

        for target in doot.args.on_fail({}).sub().keys():
            try:
                tracker.queue_entry(target, from_user=True)
            except doot.errors.TrackingError as err:
                logging.exception("Failed to Queue Target: %s : %s", target, err.args, exc_info=None)
                return

    def _queue_tasks(self, tracker) -> None:
        doot.report.trace("Queuing Initial Tasks...")
        doot.report.gap()
        for target in doot.args.on_fail([], list).cmd.args.target():
            try:
                tracker.queue_entry(target, from_user=True)
            except doot.errors.TrackingError as err:
                doot.report.warn("%s specified as run target, but it doesn't exist", target)
        else:
            doot.report.trace("%s Tasks Queued", len(tracker.active_set))


    def _choose_interrupt_handler(self) -> Maybe[bool|Callable]:
        match interrupt_handler:
            case _ if not doot.args.on_fail(False).cmd.args.interrupt():
                return None
            case None:
                return None
            case True:
                doot.report.trace("Setting default interrupt handler")
                return True
            case str():
                doot.report.trace("Loading custom interrupt handler")
                ref = CodeReference(interrupt_handler)
                return ref()
            case _:
                return None

    def _confirm_plan(self, runner:TaskRunner_i) -> bool:
        """ Confirm the plan """
        if not doot.args.on_fail(False).cmd.args.confirm():
            return True

        tracker = runner.tracker
        plan = tracker.generate_plan()
        for i,(depth,node,desc) in enumerate(plan):
            doot.report.trace("Step %-4s: %s",i, node)
        else:
            match input("Confirm Execution Plan (Y/*): "):
                case "Y":
                    return True
                case _:
                    doot.report.trace.user("Cancelling")
                    return False
