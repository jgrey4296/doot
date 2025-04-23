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
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref
# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto
from jgdv.util.plugins.selector import plugin_selector

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.cmds.core.cmd import BaseCommand
from doot.task.check_locs import CheckLocsTask


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

##--|
from doot._abstract import Command_p
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

runner_target            = doot.config.on_fail("step", str).settings.commands.step.runner()
tracker_target           = doot.config.on_fail("default", str).settings.commands.step.tracker()
reporter_target          = doot.config.on_fail("default", str).settings.commands.step.reporter()
report_line_targets      = doot.config.on_fail([]).settings.commands.run.report_line(wrapper=list)
##--|
@Proto(Command_p)
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
            self.build_param(name="<1>target", type=list[str], default=[]),
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

        doot.report.trace("- Building Task Dependency Network")
        for task in tasks.values():
            tracker.add_task(task)
        tracker.add_task(CheckLocsTask())

        doot.report.trace("- Task Dependency Network Built")

        for target in doot.args.on_fail([], list).cmd.args.target():
            if target not in tracker:
                doot.report.warn("- %s specified as run target, but it doesn't exist")
            else:
                tracker.queue_task(target)

        for target in doot.args.sub.keys():
            if target not in tracker:
                doot.report.warn(- "%s specified as run target, but it doesn't exist")
            else:
                tracker.queue_task(target)

        tracker.queue_task(CheckLocsTask.task_name)

        doot.report.trace("- %s Tasks Queued: %s", len(tracker.active_set), " ".join(tracker.active_set))
        doot.report.trace("- Running Tasks")

        with runner:
            runner()
