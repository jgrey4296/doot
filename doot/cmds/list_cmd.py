
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
from collections import defaultdict
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.cmds.base_cmd import BaseCommand
from doot.enums import TaskMeta_f
from doot.structs import ParamSpec

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
help_l  = printer.getChild("help")
cmd_l   = printer.getChild("cmd")
##-- end logging

INDENT : Final[str] = " "*8

@doot.check_protocol
class ListCmd(BaseCommand):
    _name      = "list"
    _help      = ["A simple command to list all loaded task heads."]

    @property
    def param_specs(self) -> list[ParamSpec]:
        return super().param_specs + [
            self.build_param(name="all",                                          default=True,                   desc="List all loaded tasks, by group"),
            self.build_param(name="dependencies",                                 default=False,                  desc="List task dependencies",                 prefix="--"),
            self.build_param(name="dag",       _short="D",                        default=False,                  desc="Output a DOT compatible graph of tasks", prefix="--"),
            self.build_param(name="groups",                   type=bool,          default=False,                  desc="List just the groups tasks fall into",   prefix="--"),
            self.build_param(name="by-source",                                    default=False,                  desc="List all loaded tasks, by source file",  prefix="--"),
            self.build_param(name="locations", _short="l",    type=bool,          default=False,                  desc="List all Loaded Locations"),
            self.build_param(name="internal",  _short="i",    type=bool,          default=False,                  desc="Include internal tasks (ie: prefixed with an underscore)"),
            self.build_param(name="pattern",                  type=str,           default="", positional=True,    desc="List tasks with a basic string pattern in the name"),
            ]

    def __call__(self, tasks:TomlGuard, plugins:TomlGuard):
        """List task generators"""
        logging.debug("Starting to List Jobs/Tasks")

        if (doot.args.cmd.args.pattern == ""     # type: ignore
            and not bool(doot.args.tasks)        # type: ignore
            and not doot.args.cmd.args.by_source # type: ignore
            and not doot.args.cmd.args.all):     # type: ignore
            raise doot.errors.DootCommandError("ListCmd Needs a Matcher, or all")

        if not bool(tasks):
            help_l.info("No Tasks Defined", extra={"colour": "red"})
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
        cmd_l.info("Tasks for Pattern: %s", pattern)
        for key in matches:
            spec = tasks[key]
            if TaskMeta_f.INTERNAL in spec.flags and not doot.args.cmd.args.internal:
                continue
            if TaskMeta_f.DISABLED in spec.flags:
                continue

            cmd_l.info(fmt_str,
                       spec.name,
                       spec.ctor,
                       [str(x) for x in spec.sources])

    def _print_group_matches(self, tasks):
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"    %-{max_key}s :: %-25s <%s>"
        pattern  = doot.args.cmd.args.pattern.lower()
        groups  = defaultdict(list)
        for name, spec in tasks.items():
            if pattern not in name:
                continue
            if TaskMeta_f.INTERNAL in spec.flags and not doot.args.cmd.args.internal:
                continue
            if TaskMeta_f.DISABLED in spec.flags:
                continue

            groups[spec.name.group].append((spec.name.task,
                                            spec.ctor.__module__,
                                            spec.ctor.__name__,
                                            spec.sources))

        cmd_l.info("Tasks for Matching Groups: %s", pattern, extra={"colour":"cyan"})
        for group, tasks in groups.items():
            cmd_l.info("*   %s::", group)
            for task in tasks:
                printer.info(fmt_str, *task)

    def _print_all_by_group(self, tasks):
        cmd_l.info("Defined Task Generators by Group:", extra={"colour":"cyan"})
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"{INDENT}%-{max_key}s :: %-60s :: <Source: %s>"
        groups  = defaultdict(list)
        for spec in tasks.values():
            if TaskMeta_f.INTERNAL in spec.flags and not doot.args.cmd.args.internal:
                continue
            if TaskMeta_f.DISABLED in spec.flags:
                continue


            groups[spec.name.group].append((spec.name.task,
                                            (spec.doc[0] if bool(spec.doc) else "")[:60],
                                            spec.sources))

        for group, tasks in groups.items():
            cmd_l.info("*   %s::", group, extra={"colour":"magenta"})
            for task in tasks:
                printer.info(fmt_str, *task)

        cmd_l.info("")
        cmd_l.info("Full Task Name: {group}::{task}", extra={"colour":"cyan"})

    def _print_all_by_source(self, tasks):
        cmd_l.info("Defined Task Generators by Source File:", extra={"colour":"cyan"})
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"{INDENT}%-{max_key}s :: %s.%-25s"
        sources = defaultdict(list)
        for key, spec in tasks.items():
            if TaskMeta_f.INTERNAL in spec.flags and not doot.args.cmd.args.internal:
                continue
            if TaskMeta_f.DISABLED in spec.flags:
                continue

            sources[spec.sources[0]].append((spec.name.task,
                                             spec.ctor.__module__,
                                             spec.ctor.__name__,
                                            ))

        for source, tasks in sources.items():
            cmd_l.info(":: %s ::", source, extra={"colour":"red"})
            for task in tasks:
                printer.info(fmt_str, *task)

    def _print_just_groups(self, tasks):
        cmd_l.info("Defined Task Groups:", extra={"colour":"cyan"})

        group_set = set(spec.name.group for spec in tasks.values())
        for group in group_set:
            printer.info("- %s", group)

    def _print_locations(self):
        cmd_l.info("Defined Locations: ")

        for x in sorted(doot.locs):
            printer.info("-- %-25s : %s", x, doot.locs.get(x))
