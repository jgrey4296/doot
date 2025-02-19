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
from jgdv.util.time_ctx import TimeCtx
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.cmds.base_cmd import BaseCommand, Command_p
from doot.task.check_locs import CheckLocsTask
from doot.utils.plugin_selector import plugin_selector

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
printer = doot.subprinter()
cmd_l   = doot.subprinter("cmd")
##-- end logging

# TODO make a decorator to register these onto the cmd
tracker_target           = doot.config.on_fail("default", str).settings.commands.run.tracker()
runner_target            = doot.config.on_fail("default", str).settings.commands.run.runner()
reporter_target          = doot.config.on_fail("default", str).settings.commands.run.reporter()
report_line_targets      = doot.config.on_fail([]).settings.commands.run.report_line(wrapper=list)
interrupt_handler        = doot.config.on_fail("jgdv.debugging:SignalHandler", bool|str).settings.commands.run.interrupt()

@doot.check_protocol
class RunCmd(BaseCommand):
    _name      = "run"
    _help      = ["Will perform the tasks/jobs targeted.",
                  "Can be parameterized in a commands.run block with:",
                  "tracker(str), runner(str), reporter(str), report_lines(str)",
                  ]

    @property
    def param_specs(self) -> list:
        return [
            *super().param_specs,
            self.build_param(name="step",      default=False),
            self.build_param(name="interrupt", default=False),
            self.build_param(name="dry-run",   default=False),
            self.build_param(name="confirm",   default=False),
            self.build_param(prefix=1, name="target", type=list[str], default=[]),
            ]

    def __call__(self, tasks:ChainGuard, plugins:ChainGuard):
        cmd_l.trace("---- Starting Run Cmd")
        tracker, runner = self._create_tracker_and_runner(plugins)
        interrupt       = self._choose_interrupt_handler()

        self._register_specs(tracker, tasks)
        self._queue_tasks(tracker)

        with TimeCtx(logger=logging,
                     entry_msg="--- Runner Entry",
                     exit_msg="---- Runner Exit",
                     level=20):
            with runner:
                if not self._confirm_plan(runner):
                    return

                runner(handler=interrupt)

    def _create_tracker_and_runner(self, plugins) -> tuple[TaskTracker_i, TaskRunner_i]:
        # Note the final parens to construct:
        available_reporters    = plugins.on_fail([], list).report_line()
        report_lines           = [plugin_selector(available_reporters, target=x)() for x in report_line_targets]

        match plugin_selector(plugins.on_fail([], list).reporter(), target=reporter_target):
            case None:
                pass
            case x:
                reporter = x(report_lines)

        match plugin_selector(plugins.on_fail([], list).tracker(), target=tracker_target):
            case None:
                pass
            case x:
                tracker = x()

        match plugin_selector(plugins.on_fail([], list).runner(), target=runner_target):
            case None:
                pass
            case x:
                runner = x(tracker=tracker, reporter=reporter)

        return tracker, runner

    def _register_specs(self, tracker, tasks) -> None:
        cmd_l.trace("Registering Task Specs: %s", len(tasks))
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
                cmd_l.exception("Failed to Queue Target: %s : %s", target, err.args, exc_info=None)
                return

    def _queue_tasks(self, tracker) -> None:
        cmd_l.trace("Queuing Initial Tasks")
        for target in doot.args.on_fail([], list).cmd.args.target():
            try:
                tracker.queue_entry(target, from_user=True)
            except doot.errors.TrackingError as err:
                cmd_l.warn("%s specified as run target, but it doesn't exist", target)
        else:
            cmd_l.trace("%s Tasks Queued: %s", len(tracker.active_set),
                        " ".join(str(x) for x in tracker.active_set))

    def _choose_interrupt_handler(self) -> Maybe[Callable]:
        match interrupt_handler:
            case _ if not doot.args.on_fail(False).cmd.args.interrupt():
                interrupt = None
            case None:
                interrupt = None
            case True:
                cmd_l.trace("Setting default interrupt handler")
                interrupt = interrupt_handler
            case str():
                cmd_l.trace("Loading custom interrupt handler")
                interrupt = CodeReference.build(interrupt_handler)()

    def _confirm_plan(self, runner:TaskRunner_i) -> bool:
        """ Confirm the plan """
        if not doot.args.on_fail(False).cmd.args.confirm():
            return True

        tracker = runner.tracker
        plan = tracker.generate_plan()
        for i,(depth,node,desc) in enumerate(plan):
            cmd_l.user("Step %-4s: %s",i, node)
        else:
            match input("Confirm Execution Plan (Y/*): "):
                case "Y":
                    return True
                case _:
                    cmd_l.user("Cancelling")
                    return False
