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

GROUP_INDENT : Final[str]       = " "*4
INDENT       : Final[str]       = " "*8
FMT_STR      : Final[str]       = doot.config.on_fail("{indent}{val}").settings.command.list.fmt()
hide_names   : Final[list[str]] = doot.config.on_fail([]).settings.commands.list.hide()
hide_re      : Final[Rx]        = re.compile("^({})".format("|".join(hide_names)))


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
            # List other things
            self.build_param(prefix="--", name="flags",                    type=bool, default=False, desc="List Task Meta"),
            self.build_param(prefix="--", name="loggers",                  type=bool, default=False, desc="List All Print Points"),
            self.build_param(prefix="--", name="actions",                  type=bool, default=False, desc="List All Known Actions"),
            self.build_param(prefix="--", name="plugins",                  type=bool, default=False, desc="List All Known Plugins"),
            self.build_param(prefix="--", name="locs",      _short="l",    type=bool, default=False, desc="List all Loaded Locations"),
            self.build_param(prefix="--", name="tasks",  default=True,  desc="List all loaded tasks, by group"),

            # Task Listing Parameters
            self.build_param(name="group-by", type=str, desc="How to group listed tasks")
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
        match doot.args.on_fail({}).cmd.args():
            case {"flags":True}:
                result = self._list_flags()
            case {"loggers":True}:
                result = self._list_loggers()
            case {"actions":True}:
                result = self._list_actions(plugins)
            case {"plugins":True}:
                result = self._list_plugins(plugins)
            case {"locs": True}:
                result = self._list_locations()
            case {"tasks": True}:
                result = self._list_tasks(tasks)
            case _:
                raise doot.errors.CommandError("Bad args passed in", dict(doot.args))

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

    def _build_format_string(self) -> tuple[str, dict]:
        """ Builds the format string from args"""
        pieces   = [FMT_STR]
        var_dict = {"indent": GROUP_INDENT, "val": "null"}

        # Add docstr

        # add source

        # add params

        return "".join(pieces), var_dict

    def _list_tasks(self, tasks) -> list[ListVal]:
        logging.info("---- Listing tasks")

        result = []
        result.append(("Registered Tasks/Jobs:", {"colour":"cyan"}))
        if not bool(tasks):
            result.append(("!! No Tasks Defined", {"colour":"cyan"}))
            return result

        max_key            = len(max(tasks.keys(), key=len, default="def"))
        fmt_str, base_vars = self._build_format_string()
        data : list[dict]  = []

        logging.info("-- Collecting Tasks")
        for spec in tasks.values():
            if Strang.bmark_e.hide in spec.name and not doot.args.cmd.args.internal:
                continue
            if TaskMeta_e.DISABLED in spec.meta:
                continue
            if bool(hide_names) and hide_re.search(str(spec.name)):
                continue

            data.append(
                base_vars | {
                    "indent" : " "*(1 + len(GROUP_INDENT) + len(spec.name[0:]) + 2),
                    "internal" : Strang.bmark_e.hide in spec.name,
                    "disabled" : TaskMeta_e.DISABLED in spec.meta,
                    "group"  : spec.name[0:],
                    "val"    : spec.name[1:],
                    "full"   : spec.name,
                    "docstr" : (spec.doc[0] if bool(spec.doc) else "")[:60],
                    "source" : (spec.sources[0] if bool(spec.sources) else "(No Source)"),
                },
            )

        logging.info("-- Filtering")
        match doot.args.on_fail(None).cmd.args.pattern.lower(wrapper=re.compile):
            case None:
                pass
            case re.Pattern() as reg:
                data = [x for x in data if reg.match(x['full'])]

        logging.info("-- Grouping")
        grouped = self._group_and_sort_items(data)

        logging.info("-- Formatting"
        for group, items in grouped.items():
            result.append((f"*{GROUP_INDENT}{group}::", {"colour":"magenta"}))
            for task in items:
                result.append(fmt_str.format_map(task))

        else:
            return result



    def _group_and_sort_items(self, data:list[dict]) -> dict[str,list]:
        result = defaultdict(list)

        match doot.args.on_fail(None).cmd.args.group_by():
            case None | "group":
                pass
            case "source":
                pass
            case x:
                raise ValueError("Unknown group-by arg", x)


        for val in data:
            pass

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

    def _list_loggers(self) -> list[ListVal]:
        logging.info("---- Listing Logging/Printing info")
        acceptable_names    = doot.constants.printer.PRINTER_CHILDREN
        from jgdv.logging.logger_spec import TARGETS

        result = []

        result.append("--- Primary Loggers:")
        result.append("- printer  ( target= ) : For user-facing output")
        result.append("- stream   ( target= )")
        result.append("- file     ( target= filename_fmt=%str ) ")

        result.append(None)
        result.append("--- Sub-Printer Loggers: ")
        result.append("(Additional control over user-facing output )")
        result += [f"- {x}" for x in sorted(acceptable_names)]

        result.append(None)
        result.append("--- Logging Targets: (Where a logger outputs to)")
        result += [ f"- {x}" for x in TARGETS ]

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
