#!/usr/bin/env python3
"""

"""
##-- imports

##-- end imports

##-- default imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end default imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from collections import defaultdict
from tomlguard import TomlGuard
import doot
from doot._abstract import ReportLine_i, TaskRunner_i, Reporter_i, Command_i
from doot.utils.plugin_selector import plugin_selector
from doot.task.check_locs import CheckLocsTask

printer                  = logmod.getLogger("doot._printer")

runner_target            = doot.config.on_fail("step", str).commands.step.runner()
tracker_target           = doot.config.on_fail("default", str).commands.step.tracker()
reporter_target          = doot.config.on_fail("default", str).commands.step.reporter()
report_line_targets      = doot.config.on_fail([]).commands.run.report_line(wrapper=list)

class StepCmd(Command_i):
    """
    Standard doit run command, but step through tasks
    """
    _name            = 'step'
    _help            = ["Behaves like Run, but allows user confirmation before job/task/action performance"]

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            self.make_param(name="dry-run", default=False),
            self.make_param(name="type", type=str, default="task"),
            self.make_param(name="target", type=list[str], default=[], positional=True),
            ]

    def __call__(self, tasks:TomlGuard, plugins:TomlGuard):
        # Note the final parens to construct:
        available_reporters    = plugins.on_fail([], list).report_line()
        report_lines           = [plugin_selector(available_reporters, target=x)() for x in report_line_targets]
        reporter               = plugin_selector(plugins.on_fail([], list).reporter(), target=reporter_target)(report_lines)
        tracker                = plugin_selector(plugins.on_fail([], list).tracker(), target=tracker_target)()
        runner                 = plugin_selector(plugins.on_fail([], list).runner(), target=runner_target)(tracker=tracker, reporter=reporter)

        assert(hasattr(runner, 'set_confirm_type')), "A Step Runner needs to have a confirm_type"
        runner.set_confirm_type(doot.args.cmd.args.type)

        printer.info("- Building Task Dependency Network")
        for task in tasks.values():
            tracker.add_task(task)
        tracker.add_task(CheckLocsTask())

        printer.info("- Task Dependency Network Built")

        for target in doot.args.on_fail([], list).cmd.args.target():
            if target not in tracker:
                printer.warn("- %s specified as run target, but it doesn't exist")
            else:
                tracker.queue_task(target)

        for target in doot.args.tasks.keys():
            if target not in tracker:
                printer.warn(- "%s specified as run target, but it doesn't exist")
            else:
                tracker.queue_task(target)

        tracker.queue_task(CheckLocsTask.task_name)

        printer.info("- %s Tasks Queued: %s", len(tracker.active_set), " ".join(tracker.active_set))
        printer.info("- Running Tasks")

        with runner:
            runner()
