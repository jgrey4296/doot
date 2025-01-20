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
import types
from collections import defaultdict
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.strang import CodeReference
from jgdv.util.time_ctx import TimeCtx
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot._abstract import TaskRunner_i
from doot.cmds.base_cmd import BaseCommand
from doot.task.check_locs import CheckLocsTask
from doot.utils.plugin_selector import plugin_selector

# ##-- end 1st party imports

# ##-- types
# isort: off
if TYPE_CHECKING:
   from jgdv import Maybe
   from jgdv.structs.chainguard import ChainGuard
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
        # Note the final parens to construct:
        available_reporters    = plugins.on_fail([], list).report_line()
        report_lines           = [plugin_selector(available_reporters, target=x)() for x in report_line_targets]
        reporter               = plugin_selector(plugins.on_fail([], list).reporter(), target=reporter_target)(report_lines)
        tracker                = plugin_selector(plugins.on_fail([], list).tracker(), target=tracker_target)()
        runner                 = plugin_selector(plugins.on_fail([], list).runner(), target=runner_target)(tracker=tracker, reporter=reporter)

        cmd_l.trace("Registering Task Specs: %s", len(tasks))
        for task in tasks.values():
            tracker.register_spec(task)

        cmd_l.trace("Queuing Initial Tasks")
        for target in doot.args.on_fail([], list).cmd.args.target():
            try:
                tracker.queue_entry(target, from_user=True)
            except doot.errors.TrackingError as err:
                cmd_l.warn("%s specified as run target, but it doesn't exist", target)

        tracker.queue_entry(CheckLocsTask(), from_user=True)
        for target in doot.args.on_fail({}).sub().keys():
            try:
                tracker.queue_entry(target, from_user=True)
            except doot.errors.TrackingError as err:
                cmd_l.warn("Failed to Queue Target: %s", target)
                cmd_l.debug(err)


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

        cmd_l.trace("%s Tasks Queued: %s", len(tracker.active_set), " ".join(str(x) for x in tracker.active_set))
        with TimeCtx(logger=logging, entry_msg="--- Runner Entry", exit_msg="---- Runner Exit", level=20):
            with runner:
                if doot.args.on_fail(False).cmd.args.confirm():
                    self._print_plan(runner)
                    return
                else:
                    runner(handler=interrupt)

    def _print_plan(self, runner:TaskRunner_i):
        tracker = runner.tracker
        plan = tracker.generate_plan()
        for i,(depth,node,desc) in enumerate(plan):
            cmd_l.user("Step %-4s: %s",i, node)
            match input("Confirm Execution Plan (Y/*): "):
                case "Y":
                    pass
                case _:
                    cmd_l.user("Cancelling")
