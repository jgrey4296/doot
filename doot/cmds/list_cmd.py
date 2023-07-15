
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

import doot
import doot.errors
from doot._abstract.cmd import Command_i
from collections import defaultdict


class ListCmd(Command_i):
    _name      = "list"
    _help      = ["A simple command to list all loaded task heads."]
    STATUS_MAP = {'ignore': 'I', 'up-to-date': 'U', 'run': 'R', 'error': 'E'}

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            self.make_param(name="all", default=False, desc="List all loaded tasks, by group"),
            self.make_param(name="by-source", default=False, desc="List all loaded tasks, by source file"),
            self.make_param(name="dependencies", default=False, desc="List task dependencies"),
            self.make_param(name="target", type=str, default="", positional=True, desc="List tasks with a basic string pattern in the name")
            ]

    def __call__(self, tasks, plugins):
        """List task generators"""
        logging.debug("Starting to List Taskers/Tasks")

        if (doot.args.cmd.args.target == ""
            and not doot.args.tasks
            and not doot.args.cmd.args.by_source
            and not doot.args.cmd.args.all):
            raise ValueError("ListCmd Needs a target, or all")

        # load reporter
        if 'reporter' not in plugins or not bool(plugins['reporter']):
            raise doot.errors.DootPluginError("Missing Reporter Plugin")

        if not bool(tasks):
            printer.info("No Tasks Defined")
            return


        if doot.args.cmd.args.all: # print all tasks
            self._print_all_by_group(tasks)
            return

        if doot.args.cmd.args.by_source:
            self._print_all_by_source(tasks)
            return

        # print specific tasks
        if doot.args.cmd.args.target != "":
            self._print_matches(tasks)

    def _print_matches(self, tasks):
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"%-{max_key}s :: %s.%-25s <%s>"
        target = doot.args.cmd.args.target
        matches = {x for x in tasks.keys() if target.lower() in x.lower()}
        printer.info("Tasks for Target: %s", target)
        for key in matches:
            (desc, cls) = tasks[key]
            printer.info(fmt_str, key, cls.__module__, cls.__name__, desc['source'])


    def _print_all_by_group(self, tasks):
        printer.info("Defined Task Generators by Group:")
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"    %-{max_key}s :: %s.%-25s <%s>"
        groups = defaultdict(list)
        for key, (desc, cls) in tasks.items():
            groups[desc['group']].append((fmt_str, key, cls.__module__, cls.__name__, desc['source']))

        for group, tasks in groups.items():
            printer.info("::%s::", group)
            for task in tasks:
                printer.info(*task)

    def _print_all_by_source(self, tasks):
        printer.info("Defined Task Generators by Source File:")
        max_key = len(max(tasks.keys(), key=len))
        fmt_str = f"    %-{max_key}s :: %s.%-25s <%s>"
        groups = defaultdict(list)
        for key, (desc, cls) in tasks.items():
            groups[desc['source']].append((fmt_str, key, cls.__module__, cls.__name__, desc['source']))

        for group, tasks in groups.items():
            printer.info("::%s::", group)
            for task in tasks:
                printer.info(*task)
