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
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto, Mixin
from jgdv.structs.strang import Strang
from jgdv.logging import _interface as LogAPI  # noqa: N812

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.cmds.core.cmd import BaseCommand
from doot.enums import TaskMeta_e
from doot._abstract import Command_p

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
    from jgdv import Maybe, Rx
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from jgdv.cli.param_spec import ParamSpec
    from jgdv.structs.chainguard import ChainGuard

    type ListVal = Maybe[str|tuple[str, dict]]

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

GROUP_INDENT : Final[str]       = " "*4
INDENT       : Final[str]       = " "*8
FMT_STR      : Final[str]       = doot.config.on_fail("{indent}{val}").settings.command.list.fmt()
hide_names   : Final[list[str]] = doot.config.on_fail([]).settings.commands.list.hide()
hide_re      : Final[Rx]        = re.compile("^({})".format("|".join(hide_names)))

##--|

class _DagLister_m:
    build_param : Callable

    @property
    def param_specs(self) -> list:
        return [
            *super().param_specs, # type: ignore
            self.build_param(name="--dag",
                             _short="D",
                             type=bool,
                             default=False,
                             desc="Output a DOT compatible graph of tasks"),
        ]

class _TaskLister_m:
    """
    TODO: colour jobs
    """
    build_param :  Callable

    @property
    def param_specs(self) -> list:
        return [
            *super().param_specs, # type: ignore
            self.build_param(name="-tasks",
                             type=bool,
                             default=True,
                             desc="List all loaded tasks, by group"),
            # Task Listing Parameters
            self.build_param(name="--group-by=",
                             default="group",
                             desc="How to group listed tasks"),
            self.build_param(name="+dependencies", default=False, desc="List task dependencies"),
            self.build_param(name="+internal",     default=False, desc="Include internal tasks (ie: prefixed with an underscore)"),
            self.build_param(name="+docstr", default=False),
            self.build_param(name="+params", default=False),
        ]

    def _list_tasks(self, tasks) -> list[ListVal]:
        logging.info("---- Listing tasks")

        result : list[ListVal] = []
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
                    "internal" : Strang.bmark_e.hide in spec.name, # type: ignore
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
        if doot.args.on_fail(False).cmd.args.docstr():  # noqa: FBT003
            pieces.append(" :: {docstr}")

        # add source
        if doot.args.on_fail(False).cmd.args.source():  # noqa: FBT003
            pieces.append(" :: {source}")

        # add params
        if doot.args.on_fail(False).cmd.args.params():  # noqa: FBT003
            # TODO
            pass

        if doot.args.on_fail(False).cmd.args.dependencies():  # noqa: FBT003
            # TODO
            pass

        return pieces, var_dict

    def _filter_tasks(self, data) -> list[dict]:
        logging.info("-- Filtering: %s", len(data))
        show_internal    = doot.args.on_fail(False).cmd.args.internal()  # noqa: FBT003
        no_hide_names    = bool(hide_names)
        match doot.args.on_fail(None).cmd.args.pattern.lower():
            case None | "":
                pattern = None
            case str() as x:
                pattern = re.compile(x, flags=re.IGNORECASE)

        def _filter_fn(item:dict) -> bool:
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
    build_param : Callable

    @property
    def param_specs(self) -> list:
        return [
            *super().param_specs, # type: ignore
            self.build_param(name="--locs",
                             type=bool,
                             default=False,
                             desc="List all Loaded Locations"),
        ]

    def _list_locations(self) -> list[ListVal]:
        logging.info("---- Listing Defined Locations")
        result : list[ListVal] = []
        result.append("Defined Locations: ")

        for x in sorted(doot.locs.Current):
            loc = doot.locs.Current.get(x)
            result.append(f"-- {x:<25} : {loc} ")
        else:
            return result

class _LoggerLister_m:
    build_param : Callable

    @property
    def param_specs(self) -> list:
        return [
            *super().param_specs, # type: ignore
            self.build_param(name="--loggers",
                             type=bool,
                             default=False,
                             desc="List All Print Points"),
        ]

    def _list_loggers(self) -> list[ListVal]:
        logging.info("---- Listing Logging/Printing info")
        acceptable_names    = doot.log_config._printer_children

        result : list[ListVal] = []

        result.append("--- Primary Loggers:")
        result.append("- doot.report  ( target= ) : For user-facing output")
        result.append("- stream   ( target= )")
        result.append("- file     ( target= filename_fmt=%str ) ")

        result.append(None)
        result.append("--- Sub-Printer Loggers: ")
        result.append("(Additional control over user-facing output )")
        result += [f"- {x}" for x in sorted(acceptable_names)]

        result.append(None)
        result.append("--- Logging Targets: (Where a logger outputs to)")
        result += [ f"- {x}" for x in LogAPI.TARGETS ]

        result.append(None)
        result.append("--- Notes: ")
        result.append("Format is the {} form of log formatting")
        result.append("Available variables are found here:")
        result.append("https://docs.python.org/3/library/logging.html#logrecord-attributes")
        result.append(None)
        return result

class _FlagLister_m:
    build_param : Callable

    @property
    def param_specs(self) -> list:
        return [
            *super().param_specs, # type: ignore
            self.build_param(name="--flags",
                             type=bool,
                             default=False,
                             desc="List Task Meta"),
        ]

    def _list_flags(self) -> list[ListVal]:
        logging.info("---- Listing Task Flags")
        result : list[ListVal] = []
        result.append("Task Flags: ")
        for x in sorted(doot.enums.TaskMeta_e):
            result.append(f"-- {x}")
        else:
            return result

class _ActionLister_m:
    build_param : Callable

    @property
    def param_specs(self) -> list:
        return [
            *super().param_specs, # type: ignore
            self.build_param(name="--actions",
                             type=bool,
                             default=False,
                             desc="List All Known Actions"),
        ]

    def _list_actions(self, plugins) -> list[ListVal]:
        logging.info("---- Listing Available Actions")
        result : list[ListVal] = []
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
    build_param : Callable

    @property
    def param_specs(self) -> list:
        return [
            *super().param_specs, # type: ignore
            self.build_param(name="--plugins",
                             type=bool,
                             default=False,
                             desc="List All Known Plugins"),
        ]

    def _list_plugins(self, plugins) -> list[ListVal]:
        logging.info("---- Listing Plugins")
        result : list[ListVal] = []
        result.append(("Defined Plugins by Group:", {"colour":"cyan"}))
        max_key : int   = max(["", *plugins.keys()], key=len)
        fmt_str : str   = f"{INDENT}%-{max_key}s :: %-25s"
        groups  : dict  = defaultdict(list)
        for group_str, specs in plugins.items():
            groups[group_str] += [(spec.name, spec.value) for spec in specs]

        for group, items in groups.items():
            result.append((f"*   {group}::", {"colour":"magenta"}))
            for plugin in items:
                result.append(fmt_str % plugin)

        result.append(None)
        return result

##--|

@Mixin(_TaskLister_m, _LocationLister_m, _LoggerLister_m)
@Mixin(_FlagLister_m, _ActionLister_m, _PluginLister_m)
class _Listings_m:
    pass

@Proto(Command_p)
@Mixin(_Listings_m, None, allow_inheritance=True)
class ListCmd(BaseCommand):
    build_param : Callable
    _name  = "list"
    _help  = tuple([
        "A simple command to list all loaded task heads.",
        "Set settings.commands.list.hide with a list of regexs to ignore",
    ])

    @property
    def param_specs(self) -> list[ParamSpec]:
        params = [
            *super().param_specs,
            self.build_param(name="<0>pattern", type=str,  default="", desc="Filter the listing to only values passing this regex"),
        ]
        return params

    def __call__(self, tasks:ChainGuard, plugins:ChainGuard):
        """List task generators"""
        logging.debug("Starting to List Jobs/Tasks")
        result : list[Maybe[str]] = []
        match doot.args.on_fail({}).cmd.args():
            case {"flags":True}:
                result = self._list_flags() # type: ignore
            case {"loggers":True}:
                result = self._list_loggers() # type: ignore
            case {"actions":True}:
                result = self._list_actions(plugins) # type: ignore
            case {"plugins":True}:
                result = self._list_plugins(plugins) # type: ignore
            case {"locs": True}:
                result = self._list_locations() # type: ignore
            case {"tasks": True}:
                result = self._list_tasks(tasks) # type: ignore
            case _:
                raise doot.errors.CommandError("Bad args passed in", dict(doot.args))

        self._print_text(result)
