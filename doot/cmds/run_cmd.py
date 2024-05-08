#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

# import abc
# import datetime
# import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
# from uuid import UUID, uuid1
# from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from collections import defaultdict
from tomlguard import TomlGuard
import doot
from doot.cmds.base_cmd import BaseCommand
from doot._abstract import TaskRunner_i
from doot.utils.plugin_selector import plugin_selector
from doot.task.check_locs import CheckLocsTask
from doot.structs import DootCodeReference

printer                  = logmod.getLogger("doot._printer")

tracker_target           = doot.config.on_fail("default", str).commands.run.tracker()
runner_target            = doot.config.on_fail("default", str).commands.run.runner()
reporter_target          = doot.config.on_fail("default", str).commands.run.reporter()
report_line_targets      = doot.config.on_fail([]).commands.run.report_line(wrapper=list)
interrupt_handler        = doot.config.on_fail("doot.utils.signal_handler:SignalHandler", bool|str).commands.run.interrupt()

@doot.check_protocol
class RunCmd(BaseCommand):
    _name      = "run"
    _help      = ["Will perform the tasks/jobs targeted.",
                  "Can be parameterized in a commands.run block with:",
                  "tracker(str), runner(str), reporter(str), report_lines(str)",
                  ]

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            self.build_param(name="step", default=False),
            self.build_param(name="interrupt", default=False),
            self.build_param(name="dry-run", default=False),
            self.build_param(name="target", type=list[str], default=[], positional=True),
            ]

    def __call__(self, tasks:TomlGuard, plugins:TomlGuard):
        # Note the final parens to construct:
        available_reporters    = plugins.on_fail([], list).report_line()
        report_lines           = [plugin_selector(available_reporters, target=x)() for x in report_line_targets]
        reporter               = plugin_selector(plugins.on_fail([], list).reporter(), target=reporter_target)(report_lines)
        tracker                = plugin_selector(plugins.on_fail([], list).tracker(), target=tracker_target)()
        runner                 = plugin_selector(plugins.on_fail([], list).runner(), target=runner_target)(tracker=tracker, reporter=reporter)
        printer.info("- Registering Task Specs")
        for task in tasks.values():
            tracker.register_spec(task)

        printer.info("- Queuing Initial Tasks")
        for target in doot.args.on_fail([], list).cmd.args.target():
            if target not in tracker:
                printer.warn("- %s specified as run target, but it doesn't exist")
            else:
                tracker.queue_entry(target, initial=True)

        for target in doot.args.on_fail({}).tasks().keys():
            try:
                tracker.queue_entry(target, initial=True)
            except doot.errors.DootTaskTrackingError as err:
                printer.warn("Failed to Queue Target: %s", target)
                logging.debug(err)

        tracker.queue_entry(CheckLocsTask(), initial=True)

        match interrupt_handler:
            case _ if not doot.args.cmd.args.interrupt:
                interrupt = None
            case None:
                interrupt = None
            case bool():
                interrupt = interrupt_handler
            case str():
                interrupt = DootCodeReference.build(interrupt_handler).try_import()

        printer.info("- %s Tasks Queued: %s", len(tracker.active_set), " ".join(str(x) for x in tracker.active_set))
        with runner:
            runner(handler=interrupt)
