#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- stdlib imports
from collections import defaultdict

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.cmds.base_cmd import BaseCommand
from doot.task.check_locs import CheckLocsTask
from doot.utils.plugin_selector import plugin_selector

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

runner_target            = doot.config.on_fail("step", str).settings.commands.step.runner()
tracker_target           = doot.config.on_fail("default", str).settings.commands.step.tracker()
reporter_target          = doot.config.on_fail("default", str).settings.commands.step.reporter()
report_line_targets      = doot.config.on_fail([]).settings.commands.run.report_line(wrapper=list)

class StepCmd(BaseCommand):
    """
    Standard doit run command, but step through tasks
    """
    _name            = 'step'
    _help            = ["Behaves like Run, but allows user confirmation before job/task/action performance"]

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            self.build_param(name="dry-run", default=False),
            self.build_param(name="type", type=str, default="task"),
            self.build_param(prefix=1, name="target", type=list[str], default=[]),
            ]

    def __call__(self, tasks:ChainGuard, plugins:ChainGuard):
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

        for target in doot.args.sub.keys():
            if target not in tracker:
                printer.warn(- "%s specified as run target, but it doesn't exist")
            else:
                tracker.queue_task(target)

        tracker.queue_task(CheckLocsTask.task_name)

        printer.info("- %s Tasks Queued: %s", len(tracker.active_set), " ".join(tracker.active_set))
        printer.info("- Running Tasks")

        with runner:
            runner()
