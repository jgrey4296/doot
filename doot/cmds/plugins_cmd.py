#!/usr/bin/env python3
"""
A Doot Command to report on plugins found on the system
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

from collections import defaultdict
from jgdv.structs.chainguard import ChainGuard
from jgdv.cli.param_spec import ParamSpec
import doot
import doot.errors
from doot.cmds.base_cmd import BaseCommand

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

INDENT : Final[str] = " "*8

@doot.check_protocol
class PluginsCmd(BaseCommand):
    _name      = "plugins"
    _help      = ["A simple command to list all loaded plugins."]

    @property
    def param_specs(self) -> list[ParamSpec]:
        return super().param_specs + [
            self.build_param(name="all",                  default=True,                   desc="List all loaded tasks, by group"),
            self.build_param(name="groups",    type=bool, default=False,                  desc="List just the groups tasks fall into",   prefix="--"),
            self.build_param(name="pattern",   type=str,  default="", positional=True,    desc="List tasks with a basic string pattern in the name"),
            ]

    def __call__(self, tasks:ChainGuard, plugins:ChainGuard):
        """List task generators"""
        logging.debug("Starting to List System Plugins ")

        if not bool(plugins):
            printer.info("No Tasks Defined")
            return

        if doot.args.cmd.args.pattern != "":
            self._print_group_matches(plugins)
            return

        self._print_all_by_group(plugins)

    def _print_matches(self, plugins):
        max_key = len(max(plugins.keys(), key=len))
        fmt_str = f"%-{max_key}s :: %-25s <%s>"
        pattern = doot.args.cmd.args.pattern.lower()
        matches = {x for x in plugins.keys() if pattern in x.lower()}
        printer.info("Plugins for Pattern: %s", pattern)
        for key in matches:
            spec = plugins[key]
            printer.info(fmt_str,
                         spec.name,
                         spec.ctor,
                         spec.sources)

    def _print_group_matches(self, plugins):
        max_key = len(max(plugins.keys(), key=len))
        fmt_str = f"{INDENT}%-{max_key}s :: %-25s"
        pattern  = re.compile(doot.args.cmd.args.pattern.lower())
        groups  = defaultdict(list)
        for group_name, specs in plugins.items():
            if pattern.search(group_name):
                groups[group_name] += [(spec.name, spec.value) for spec in specs]
            else:
                groups[group_name] += [(spec.name, spec.value) for spec in specs if pattern.search(spec.name) or pattern.search(spec.value)]

        printer.info("Plugins for Matching Groups: %s", doot.args.cmd.args.pattern.lower())
        for group, plugins in groups.items():
            if not bool(plugins):
                continue
            printer.info("*   %s::", group)
            for plugin in plugins:
                printer.info(fmt_str, *plugin)

    def _print_all_by_group(self, plugins):
        printer.info("Defined Plugins by Group:", extra={"colour":"cyan"})
        max_key = len(max(plugins.keys(), key=len))
        fmt_str = f"{INDENT}%-{max_key}s :: %-25s"
        groups  = defaultdict(list)
        pass
        for group_str, specs in plugins.items():
            groups[group_str] += [(spec.name, spec.value) for spec in specs]

        for group, plugins in groups.items():
            printer.info("*   %s::", group, extra={"colour":"magenta"})
            for plugin in plugins:
                printer.info(fmt_str, *plugin)

        printer.info("")
