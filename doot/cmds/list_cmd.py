#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN001
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
import typing
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
from jgdv.structs.strang import Strang

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.cmds.base_cmd import BaseCommand
from doot.enums import TaskMeta_e

# ##-- end 1st party imports

# ##-- typecheck imports
# isort: off
if typing.TYPE_CHECKING:
   from jgdv import Maybe, Rx
   from jgdv.cli.param_spec import ParamSpec
   from jgdv.structs.chainguard import ChainGuard

   type ListVal = Maybe[str | (str, dict)]

# isort: on
# ##-- end typecheck imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
help_l  = doot.subprinter("help")
cmd_l   = doot.subprinter("cmd")
##-- end logging

INDENT     : Final[str]       = " "*8
hide_names : Final[list[str]] = doot.config.on_fail([]).settings.commands.list.hide()
hide_re    : Final[Rx]        = re.compile("^({})".format("|".join(hide_names)))


@doot.check_protocol
class ListCmd(BaseCommand):
    _name      = "list"
    _help  : ClassVar[list[str]]    = [
        "A simple command to list all loaded task heads.",
        "Set settings.commands.list.hide with a list of regexs to ignore",
    ]

    @property
    def param_specs(self) -> list[ParamSpec]:
        return [
            *super().param_specs,
            self.build_param(prefix="--", name="flags",                    type=bool, default=False, desc="List Task Meta"),
            self.build_param(prefix="--", name="printers",                 type=bool, default=False, desc="List All Print Points"),
            self.build_param(prefix="--", name="actions",                  type=bool, default=False, desc="List All Known Actions"),
            self.build_param(prefix="--", name="plugins",                  type=bool, default=False, desc="List All Known Plugins"),
            self.build_param(prefix="--", name="locs",      _short="l",    type=bool, default=False, desc="List all Loaded Locations"),

            self.build_param(name="all",  default=True,  desc="List all loaded tasks, by group"),
            self.build_param(name="dependencies",             type=bool, default=False, desc="List task dependencies"),
            self.build_param(name="dag",       _short="D",    type=bool, default=False, desc="Output a DOT compatible graph of tasks"),
            self.build_param(name="groups",                   type=bool, default=False, desc="List just the groups tasks fall into"),
            self.build_param(name="by-source",                type=bool, default=False, desc="List all loaded tasks, by source file"),
            self.build_param(name="internal",  _short="i",    type=bool, default=False, desc="Include internal tasks (ie: prefixed with an underscore)"),

            self.build_param(prefix=1, name="pattern", type=str,  default="", desc="Filter the listing to only values passing this regex"),
            ]

    def __call__(self, tasks:ChainGuard, plugins:ChainGuard):
        """List task generators"""
        logging.debug("Starting to List Jobs/Tasks")
        result : list[Maybe[str]] = []
        match dict(doot.args.cmd.args):
            case {"flags":True}:
                result = self._list_flags()
            case {"printers":True}:
                result = self._list_printers()
            case {"actions":True}:
                result = self._list_actions(plugins)
            case {"plugins":True}:
                result = self._list_plugins(plugins)
            case {"locs": True}:
                result = self._list_locations()

        match dict(doot.args.cmd.args):
            case _ if bool(result):
                pass
            case {"by-source": True}:
                result = self._list_tasks_by_source(tasks)
            case {"groups": True, "pattern": x} if bool(x):
                result = self._list_tasks_group_matches(tasks)
            case {"groups": True}:
                result = self._list_task_groups(tasks)
            case {"pattern": x} if bool(x):
                result = self._list_tasks_matches(tasks)
            case {"all": True}:
                result = self._list_tasks_all_by_group(tasks)
            case _:
                raise doot.errors.CommandError("Bad args passed in", doot.args.cmd.args)

        self._print_text(result)

    def _print_text(self, text:list[ListVal]) -> None:
        for line in text:
            match line:
                case str():
                    cmd_l.info(line)
                case (str() as s, dict() as d):
                    cmd_l.info(s, extra=d)
                case None:
                    cmd_l.info("")


    def _list_tasks_matches(self, tasks) -> list[ListVal]:
        logging.info("---- Listing Matching Tasks")
        result = []
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"%-{max_key}s :: %-25s <%s>"
        pattern = doot.args.cmd.args.pattern.lower()
        matches = {x for x in tasks.keys() if pattern in x.lower()}
        result.append(f"Tasks for Pattern: {pattern}")
        for key in matches:
            spec = tasks[key]
            if Strang.bmark_e.hide in spec.name and not doot.args.cmd.args.internal:
                continue
            if TaskMeta_e.DISABLED in spec.meta:
                continue

            result.append(fmt_str % (spec.name,
                                     spec.ctor,
                                     [str(x) for x in spec.sources]))
        else:
            return result

    def _list_tasks_group_matches(self, tasks) -> list[ListVal]:
        logging.info("---- Listing matching Tasks by Matching Group")
        result   = []
        max_key  = len(max(tasks.keys(), key=len))
        fmt_str  = f"    %-{max_key}s :: %-25s <%s>"
        pattern  = doot.args.cmd.args.pattern.lower()
        groups   = defaultdict(list)
        for name, spec in tasks.items():
            if pattern not in name:
                continue
            if Strang.bmark_e.hide in spec.name and not doot.args.cmd.args.internal:
                continue
            if TaskMeta_e.DISABLED in spec.meta:
                continue

            groups[spec.name[0:]].append(
                (spec.name[1:], spec.ctor.__module__, spec.ctor.__name__, spec.sources),
            )

        result.append((f"Tasks for Matching Groups: {pattern}", {"colour":"cyan"}))
        for group, items in groups.items():
            result.append(f"*   {group}::")
            for task in items:
                result.append(fmt_str % task)
        else:
            return result

    def _list_tasks_all_by_group(self, tasks) -> list[ListVal]:
        logging.info("---- Listing all tasks by group")
        result = []
        result.append(("Defined Task Generators by Group:", {"colour":"cyan"}))
        max_key = len(max(tasks.keys(), key=len, default="def"))
        fmt_str = f"{INDENT}%-{max_key}s :: %-60s :: <Source: %s>"
        groups  = defaultdict(list)

        if not bool(tasks):
            result.append(("!! No Tasks Defined", {"colour":"cyan"}))

        for spec in tasks.values():
            if Strang.bmark_e.hide in spec.name and not doot.args.cmd.args.internal:
                continue
            if TaskMeta_e.DISABLED in spec.meta:
                continue
            if bool(hide_names) and hide_re.search(str(spec.name)):
                continue

            groups[spec.name[0:]].append(
                (
                    spec.name[1:],
                    (spec.doc[0] if bool(spec.doc) else "")[:60],
                    (spec.sources[0] if bool(spec.sources) else "(No Source)"),
                ),
            )


        for group, items in groups.items():
            result.append((f"*   {group}::", {"colour":"magenta"}))
            for task in items:
                result.append(fmt_str % task)

        result.append(None)
        result.append(("Full Task Name: {group}::{task}", {"colour":"cyan"}))

        return result

    def _list_tasks_by_source(self, tasks) -> list[ListVal]:
        logging.info("---- Listing Tasks by source file")
        result = []
        result.append(("Defined Task Generators by Source File:", {"colour":"cyan"}))
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"{INDENT}%-{max_key}s :: %s.%-25s"
        sources = defaultdict(list)
        for spec in tasks.values():
            if TaskMeta_e.INTERNAL in spec.meta and not doot.args.cmd.args.internal:
                continue
            if TaskMeta_e.DISABLED in spec.meta:
                continue

            sources[spec.sources[0]].append(
                (
                    spec.name[1:],
                    spec.ctor.__module__,
                    spec.ctor.__name__,
                ),
            )

        for source, items in sources.items():
            result.append((f":: {source} ::", {"colour":"red"}))
            for task in items:
                result.append(fmt_str % task)
        else:
            return result

    def _list_task_groups(self, tasks) -> list[ListVal]:
        logging.info("---- Listing Task Groups")
        result = []
        result.append(("Defined Task Groups:", {"colour":"cyan"}))

        group_set = set(spec.name[0:] for spec in tasks.values())
        for group in group_set:
            result.append(f"- {group}")
        else:
            return result

    def _list_locations(self) -> list[ListVal]:
        logging.info("---- Listing Defined Locations")
        result = []
        result.append("Defined Locations: ")

        for x in sorted(doot.locs.Current):
            loc = doot.locs.Current.get(x)
            result.append(f"-- {x:-25} : {loc} ")
        else:
            return result

    def _list_printers(self) -> list[ListVal]:
        logging.info("---- Listing Printers/Logging info")
        acceptable_names    = doot.constants.printer.PRINTER_CHILDREN
        from jgdv.logging.logger_spec import TARGETS

        result = []

        result.append("--- Logging Targets:")
        result.append(", ".join(TARGETS))

        result.append(None)
        result.append("--- Subprinters: ")
        result.append(", ".join(acceptable_names))

        result.append(None)
        result.append("--- Notes: ")
        result.append("Format is the {} form of log formatting")
        result.append("Available variables are found here:")
        result.append("https://docs.python.org/3/library/logging.html#logrecord-attributes")
        result.append(None)
        return result

    def _list_flags(self) -> list[ListVal]:
        logging.info("---- Listing Task Flags")
        result = []
        result.append("Task Flags: ")
        for x in sorted(doot.enums.TaskMeta_e, key=lambda x: x.name):
            result.append(f"-- {x.name}")
        else:
            return result

    def _list_actions(self, plugins) -> list[ListVal]:
        logging.info("---- Listing Available Actions")
        result = []
        result.append("Available Actions:")
        for action in sorted(plugins.action, key=lambda x: x.name):
            result.append(f"-- {action.name:-20} : {action.value}")

        result.append(None)
        result.append("- For Custom Python Actions, implement the following in the .tasks directory")
        result.append("def custom_action(spec:ActionSpec, task_state:dict) -> Maybe[bool|dict]:...")
        return result

    def _list_plugins(self, plugins) -> list[ListVal]:
        logging.info("---- Listing Plugins")
        result = []
        result.append(("Defined Plugins by Group:", {"colour":"cyan"}))
        max_key = len(max(plugins.keys(), key=len))
        fmt_str = f"{INDENT}%-{max_key}s :: %-25s"
        groups  = defaultdict(list)
        pass
        for group_str, specs in plugins.items():
            groups[group_str] += [(spec.name, spec.value) for spec in specs]

        for group, items in groups.items():
            result.append((f"*   {group}::", {"colour":"magenta"}))
            for plugin in items:
                result.append(fmt_str % plugin)

        result.append(None)
        return result
