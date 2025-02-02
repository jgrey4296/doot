#!/usr/bin/env python3
"""
The command which provides the user a listing of... things.

Each mixin does the work of creating the list, and provides its own
set of cli args.
The actual ListCmd joins them all and calls the necessary method,
passing the result to the generic command _print_text method
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

class _DagLister_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(prefix="--",
                                 name="dag",
                                 _short="D",
                                 type=bool,
                                 default=False,
                                 desc="Output a DOT compatible graph of tasks"),
                ]

class _TaskLister_m:
    """
    TODO: colour jobs
    """

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(prefix="--",
                                 name="tasks",
                                 default=True,
                                 desc="List all loaded tasks, by group"),
                # Task Listing Parameters
                self.build_param(name="group-by",
                                 type=str,
                                 default="group",
                                 desc="How to group listed tasks"),
                self.build_param(prefix="+", name="dependencies",
                                 type=bool, default=False, desc="List task dependencies"),
                self.build_param(prefix="+", name="internal",  _short="i",
                                 type=bool, default=False, desc="Include internal tasks (ie: prefixed with an underscore)"),
                self.build_param(prefix="+", name="docstr", type=bool, default=False),
                self.build_param(prefix="+", name="params", type=bool, default=False),
                ]

    def _list_tasks(self, tasks) -> list[ListVal]:
        logging.info("---- Listing tasks")

        result = []
        result.append(("Registered Tasks/Jobs:", {"colour":"cyan"}))
        if not bool(tasks):
            result.append(("!! No Tasks Defined", {"colour":"cyan"}))
            return result

        max_key            = len(max(tasks.keys(), key=len, default="def"))
        fmt_strs, base_vars = self._build_format_strings()
        data : list[dict]  = []

        logging.info("-- Collecting Tasks")
        for spec in tasks.values():
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

        data    = self._filter_tasks(data)
        grouped = self._group_tasks(data)

        logging.info("-- Formatting")
        for group, items in grouped.items():
            result.append((f"*{GROUP_INDENT}{group}::", {"colour":"magenta"}))
            for task in items:
                result.append(" ".join(x.format_map(task) for x in fmt_strs))

        else:
            return result

    def _build_format_strings(self) -> tuple[list[str], dict]:
        """ Builds the format string from args"""
        pieces   = []
        var_dict = {"indent": GROUP_INDENT, "val": "null"}

        match doot.args.on_fail(None).cmd.args.group_by():
            case "source":
                pieces.append("- {full}")
            case _:
                pieces.append(FMT_STR)

        # Add docstr
        if doot.args.on_fail(False).cmd.args.docstr():
            pieces.append(" :: {docstr}")

        # add source
        if doot.args.on_fail(False).cmd.args.source():
            pieces.append(" :: {source}")

        # add params
        if doot.args.on_fail(False).cmd.args.params():
            # TODO
            pass

        if doot.args.on_fail(False).cmd.args.dependencies():
            # TODO
            pass

        return pieces, var_dict

    def _filter_tasks(self, data) -> list[dict]:
        logging.info("-- Filtering: %s", len(data))
        show_internal    = doot.args.on_fail(False).cmd.args.internal()
        no_hide_names    = bool(hide_names)
        match doot.args.on_fail(None).cmd.args.pattern.lower():
            case None | "":
                pattern = None
            case str() as x:
                pattern = re.compile(x, flags=re.IGNORECASE)

        def _filter_fn(item):
            return all([not item['disabled'],
                        show_internal or not item['internal'],
                        pattern is None or pattern.match(item['full']),
                        no_hide_names or hide_re.search(item['full']),
                        ])

        return list(filter(_filter_fn, data))

    def _group_tasks(self, data:list[dict]) -> dict[str,list]:
        logging.info("-- Grouping: %s", len(data))
        result = defaultdict(list)

        match doot.args.on_fail(None).cmd.args.group_by():
            case None | "group":

                def _group_fn(item) -> str:
                    return item['group']
            case "source":

                def _group_fn(item) -> str:
                    return item['source']
            case x:
                raise ValueError("Unknown group-by arg", x)

        for item in data:
            result[_group_fn(item)].append(item)

        return result

class _LocationLister_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(prefix="--",
                                 name="locs",
                                 _short="l",
                                 type=bool,
                                 default=False,
                                 desc="List all Loaded Locations"),
                ]

    def _list_locations(self) -> list[ListVal]:
        logging.info("---- Listing Defined Locations")
        result = []
        result.append("Defined Locations: ")

        for x in sorted(doot.locs.Current):
            loc = doot.locs.Current.get(x)
            result.append(f"-- {x:<25} : {loc} ")
        else:
            return result

class _LoggerLister_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(prefix="--",
                                 name="loggers",
                                 type=bool,
                                 default=False,
                                 desc="List All Print Points"),
                ]

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

class _FlagLister_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(prefix="--",
                                 name="flags",
                                 type=bool,
                                 default=False,
                                 desc="List Task Meta"),
                ]

    def _list_flags(self) -> list[ListVal]:
        logging.info("---- Listing Task Flags")
        result = []
        result.append("Task Flags: ")
        for x in sorted(doot.enums.TaskMeta_e, key=lambda x: x.name):
            result.append(f"-- {x.name}")
        else:
            return result

class _ActionLister_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(prefix="--",
                                 name="actions",
                                 type=bool,
                                 default=False,
                                 desc="List All Known Actions"),
                ]

    def _list_actions(self, plugins) -> list[ListVal]:
        logging.info("---- Listing Available Actions")
        result = []
        result.append("Available Actions:")
        name_lens = [len(x.name) for x in plugins.action]
        largest = max([0, *name_lens])
        for action in sorted(plugins.action, key=lambda x: x.name):
            result.append(f"-- {action.name:<25} : {action.value}")

        result.append(None)
        result.append("- For Custom Python Actions, implement the following in the .tasks directory")
        result.append("def custom_action(spec:ActionSpec, task_state:dict) -> Maybe[bool|dict]:...")
        return result

class _PluginLister_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(prefix="--",
                                 name="plugins",
                                 type=bool,
                                 default=False,
                                 desc="List All Known Plugins"),
                ]

    def _list_plugins(self, plugins) -> list[ListVal]:
        logging.info("---- Listing Plugins")
        result = []
        result.append(("Defined Plugins by Group:", {"colour":"cyan"}))
        max_key = max(["", *plugins.keys()], key=len)
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

@doot.check_protocol
class ListCmd(_TaskLister_m,
              _LocationLister_m,
              _LoggerLister_m,
              _FlagLister_m,
              _ActionLister_m,
              _PluginLister_m,
              BaseCommand):
    _name      = "list"
    _help  : ClassVar[list[str]]    = [
        "A simple command to list all loaded task heads.",
        "Set settings.commands.list.hide with a list of regexs to ignore",
    ]

    @property
    def param_specs(self) -> list[ParamSpec]:
        return [
            *super().param_specs,
            self.build_param(prefix=1, name="pattern",        type=str,  default="", desc="Filter the listing to only values passing this regex"),
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
