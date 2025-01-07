
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
from jgdv import Maybe, Rx
from jgdv.structs.chainguard import ChainGuard
from jgdv.cli.param_spec import ParamSpec
from jgdv.structs.strang import Strang
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.cmds.base_cmd import BaseCommand
from doot.enums import TaskMeta_e

# ##-- end 1st party imports

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
    _help      = [
        "A simple command to list all loaded task heads."
        "Set settings.commands.list.hide with a list of regexs to ignore"
    ]

    @property
    def param_specs(self) -> list[ParamSpec]:
        return super().param_specs + [
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
        if not any(x for x in [bool(doot.args.on_fail("").cmd.args.pattern()),
                               bool(doot.args.sub),
                               doot.args.on_fail(False).cmd.args.by_source(),
                               doot.args.on_fail(False).cmd.args.all(),
                               ]):
            raise doot.errors.CommandError("ListCmd Needs a Matcher, or all")

        match dict(doot.args.cmd.args):
            case {"flags":True}:
                self._list_flags()
                return
            case {"printers":True}:
                self._list_printers()
                return
            case {"actions":True}:
                self._list_actions(plugins)
                return
            case {"plugins":True}:
                self._list_plugins(plugins)
                return
            case {"locs": True}:
                self._list_locations()
                return

        if not bool(tasks):
            help_l.info("No Tasks Defined", extra={"colour": "red"})
            return

        match dict(doot.args.cmd.args):
            case {"by-source": True}:
                self._list_tasks_by_source(tasks)
            case {"groups": True, "pattern": x} if bool(x):
                self._list_tasks_group_matches(tasks)
            case {"groups": True}:
                self._list_task_groups(tasks)
            case {"pattern": x} if bool(x):
                self._list_tasks_matches(tasks)
            case {"all": True}:
                self._list_tasks_all_by_group(tasks)
            case _:
                raise doot.errors.CommandError("Bad args passed in", doot.args.cmd.args)

    def _list_tasks_matches(self, tasks):
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"%-{max_key}s :: %-25s <%s>"
        pattern = doot.args.cmd.args.pattern.lower()
        matches = {x for x in tasks.keys() if pattern in x.lower()}
        cmd_l.info("Tasks for Pattern: %s", pattern)
        for key in matches:
            spec = tasks[key]
            if Strang.bmark_e.hide in spec.name and not doot.args.cmd.args.internal:
                continue
            if TaskMeta_e.DISABLED in spec.meta:
                continue

            cmd_l.info(fmt_str,
                       spec.name,
                       spec.ctor,
                       [str(x) for x in spec.sources])

    def _list_tasks_group_matches(self, tasks):
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"    %-{max_key}s :: %-25s <%s>"
        pattern  = doot.args.cmd.args.pattern.lower()
        groups  = defaultdict(list)
        for name, spec in tasks.items():
            if pattern not in name:
                continue
            if Strang.bmark_e.hide in spec.name and not doot.args.cmd.args.internal:
                continue
            if TaskMeta_e.DISABLED in spec.meta:
                continue

            groups[spec.name[0:]].append((spec.name[1:],
                                          spec.ctor.__module__,
                                          spec.ctor.__name__,
                                          spec.sources))

        cmd_l.info("Tasks for Matching Groups: %s", pattern, extra={"colour":"cyan"})
        for group, tasks in groups.items():
            cmd_l.info("*   %s::", group)
            for task in tasks:
                printer.info(fmt_str, *task)

    def _list_tasks_all_by_group(self, tasks):
        cmd_l.info("Defined Task Generators by Group:", extra={"colour":"cyan"})
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"{INDENT}%-{max_key}s :: %-60s :: <Source: %s>"
        groups  = defaultdict(list)
        for spec in tasks.values():
            if Strang.bmark_e.hide in spec.name and not doot.args.cmd.args.internal:
                continue
            if TaskMeta_e.DISABLED in spec.meta:
                continue
            if bool(hide_names) and hide_re.search(str(spec.name)):
                continue

            groups[spec.name[0:]].append((spec.name[1:],
                                          (spec.doc[0] if bool(spec.doc) else "")[:60],
                                          (spec.sources[0] if bool(spec.sources) else "None")
                                           ))


        for group, tasks in groups.items():
            cmd_l.info("*   %s::", group, extra={"colour":"magenta"})
            for task in tasks:
                printer.info(fmt_str, *task)

        cmd_l.info("")
        cmd_l.info("Full Task Name: {group}::{task}", extra={"colour":"cyan"})

    def _list_tasks_by_source(self, tasks):
        cmd_l.info("Defined Task Generators by Source File:", extra={"colour":"cyan"})
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"{INDENT}%-{max_key}s :: %s.%-25s"
        sources = defaultdict(list)
        for key, spec in tasks.items():
            if TaskMeta_e.INTERNAL in spec.meta and not doot.args.cmd.args.internal:
                continue
            if TaskMeta_e.DISABLED in spec.meta:
                continue

            sources[spec.sources[0]].append((spec.name[1:],
                                             spec.ctor.__module__,
                                             spec.ctor.__name__,
                                            ))

        for source, tasks in sources.items():
            cmd_l.info(":: %s ::", source, extra={"colour":"red"})
            for task in tasks:
                printer.info(fmt_str, *task)

    def _list_task_groups(self, tasks):
        cmd_l.info("Defined Task Groups:", extra={"colour":"cyan"})

        group_set = set(spec.name[0:] for spec in tasks.values())
        for group in group_set:
            printer.info("- %s", group)

    def _list_locations(self):
        cmd_l.info("Defined Locations: ")

        for x in sorted(doot.locs.Current):
            printer.info("-- %-25s : %s", x, doot.locs.Current.get(x))


    def _list_printers(self):
        logging.info("---- Listing Printers/Logging info")
        acceptable_names    = doot.constants.printer.PRINTER_CHILDREN

        cmd_l.info("")
        cmd_l.info("--- Logging Targets:")
        cmd_l.info("%s", ", ".join(["file", "stdout", "stderr", "rotate"]))

        cmd_l.info("")
        cmd_l.info("--- Subprinters: ")
        cmd_l.info("%s", ", ".join(acceptable_names))

        cmd_l.info("")
        cmd_l.info("--- Notes: ")
        cmd_l.info("Format is the {} form of log formatting")
        cmd_l.info("Available variables are found here:")
        cmd_l.info("https://docs.python.org/3/library/logging.html#logrecord-attributes")
        cmd_l.info("")

    def _list_flags(self):
        logging.info("---- Listing Task Flags")
        cmd_l.info("Task Flags: ")
        for x in sorted(doot.enums.TaskMeta_e, key=lambda x: x.name):
            cmd_l.info("-- %s", x.name)

    def _list_actions(self, plugins):
        cmd_l.info("Available Actions:")
        for action in sorted(plugins.action, key=lambda x: x.name):
            cmd_l.info("-- %-20s : %s", action.name, action.value)

        cmd_l.info("")
        cmd_l.info("- For Custom Python Actions, implement the following in the .tasks directory")
        cmd_l.info("def custom_action(spec:ActionSpec, task_state:dict) -> Maybe[bool|dict]:...")

    def _list_plugins(self, plugins):
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
