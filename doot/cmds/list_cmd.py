
#!/usr/bin/env python3
"""

"""
##-- imports
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

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

from collections import defaultdict
from tomler import Tomler
import doot
import doot.errors
from doot._abstract import Command_i
from doot.structs import DootParamSpec


INDENT : Final[str] = " "*8

@doot.check_protocol
class ListCmd(Command_i):
    _name      = "list"
    _help      = ["A simple command to list all loaded task heads."]
    STATUS_MAP = {'ignore': 'I', 'up-to-date': 'U', 'run': 'R', 'error': 'E'}

    @property
    def param_specs(self) -> list[DootParamSpec]:
        return super().param_specs + [
            self.make_param(name="all",                                          default=True,                   desc="List all loaded tasks, by group"),
            self.make_param(name="dependencies",                                 default=False,                  desc="List task dependencies",                 prefix="--"),
            self.make_param(name="dag",       _short="D",                        default=False,                  desc="Output a DOT compatible graph of tasks", prefix="--"),
            self.make_param(name="groups",                   type=bool,          default=False,                  desc="List just the groups tasks fall into",   prefix="--"),
            self.make_param(name="by-source",                                    default=False,                  desc="List all loaded tasks, by source file",  prefix="--"),
            self.make_param(name="pattern",                  type=str,           default="", positional=True,    desc="List tasks with a basic string pattern in the name"),
            self.make_param(name="locations", _short="l",    type=bool,          default=False,                  desc="List all Loaded Locations")
            ]

    def __call__(self, tasks:Tomler, plugins:Tomler):
        """List task generators"""
        logging.debug("Starting to List Taskers/Tasks")

        if (doot.args.cmd.args.pattern == ""     # type: ignore
            and not bool(doot.args.tasks)        # type: ignore
            and not doot.args.cmd.args.by_source # type: ignore
            and not doot.args.cmd.args.all):     # type: ignore
            raise doot.errors.DootCommandError("ListCmd Needs a Matcher, or all")

        # load reporter
        if 'reporter' not in plugins or not bool(plugins['reporter']):
            raise doot.errors.DootPluginError("Missing Reporter Plugin")

        if not bool(tasks):
            printer.info("No Tasks Defined")
            return

        match dict(doot.args.cmd.args): # type: ignore
            case {"locations": True}:
                self._print_locations()
            case {"by-source": True}:
                self._print_all_by_source(tasks)
            case {"groups": True, "pattern": x} if bool(x):
                self._print_group_matches(tasks)
            case {"groups": True}:
                self._print_just_groups(tasks)
            case {"pattern": x} if bool(x):
                self._print_matches(tasks)
            case {"all": True}:
                self._print_all_by_group(tasks)
            case _:
                raise doot.errors.DootCommandError("Bad args passed in", doot.args.cmd.args)

    def _print_matches(self, tasks):
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"%-{max_key}s :: %-25s <%s>"
        pattern = doot.args.cmd.args.pattern.lower()
        matches = {x for x in tasks.keys() if pattern in x.lower()}
        printer.info("Tasks for Pattern: %s", pattern)
        for key in matches:
            spec = tasks[key]
            printer.info(fmt_str,
                         spec.name,
                         spec.ctor_name,
                         spec.source)

    def _print_group_matches(self, tasks):
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"    %-{max_key}s :: %-25s <%s>"
        pattern  = doot.args.cmd.args.pattern.lower()
        groups  = defaultdict(list)
        for name, spec in tasks.items():
            if pattern not in name:
                continue
            groups[spec.name.group_str()].append((spec.name.task_str(),
                                                  spec.ctor.__module__,
                                                  spec.ctor.__name__,
                                                  spec.source))

        printer.info("Tasks for Matching Groups: %s", pattern)
        for group, tasks in groups.items():
            printer.info("*   %s::", group)
            for task in tasks:
                printer.info(fmt_str, *task)

    def _print_all_by_group(self, tasks):
        printer.info("Defined Task Generators by Group:")
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"{INDENT}%-{max_key}s :: %-25s <%s>"
        groups  = defaultdict(list)
        for spec in tasks.values():
            groups[spec.name.group_str()].append((spec.name.task_str(),
                                                  spec.ctor_name,
                                                  spec.source))

        for group, tasks in groups.items():
            printer.info("*   %s::", group)
            for task in tasks:
                printer.info(fmt_str, *task)

        printer.info("")
        printer.info("Full Task Name: {group}::{task}")

    def _print_all_by_source(self, tasks):
        printer.info("Defined Task Generators by Source File:")
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"{INDENT}%-{max_key}s :: %s.%-25s <%s>"
        sources = defaultdict(list)
        for key, (desc, cls) in tasks.items():
            sources[desc['source']].append((spec.name.task_str(),
                                            spec.ctor.__module__,
                                            spec.ctor.__name__,
                                            spec.source))

        for source, tasks in sources.items():
            printer.info("::%s::", source)
            for task in tasks:
                printer.info(fmt_str, *task)


    def _print_just_groups(self, tasks):
        printer.info("Defined Task Groups:")

        group_set = set(spec.name.group_str() for spec in tasks.values())
        for group in group_set:
            printer.info("- %s", group)


    def _print_locations(self):
        printer.info("Defined Locations: ")

        for x in sorted(doot.locs):
            printer.info("-- %-25s : %s", x, doot.locs.get(x))
