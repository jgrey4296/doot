#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
# import abc
# import datetime
# import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from collections import defaultdict
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.code_ref import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.cmds.base_cmd import BaseCommand
from doot.structs import ParamSpec, TaskSpec

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
cmd_l   = doot.subprinter("cmd")
##-- end logging

NON_DEFAULT_KEY : Final[str] = doot.constants.misc.NON_DEFAULT_KEY

LINE_SEP        : Final[str] = "------------------------------"
GROUP_INDENT    : Final[str] = "----"
ITEM_INDENT     : Final[str] = "-"

class HelpCmd(BaseCommand):
    _name      = "help"
    _help      = ["Print info about the specified cmd or task",
                  "Can also be triggered by passing --help to any command or task"
                  ]

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            # self.build_param(name="target", type=str, default=""),
            self.build_param(name="target", type=str, positional=True, default="", desc="The target to get help about. A command or task.")
            ]

    def __call__(self, tasks, plugins):
        """List task generators"""
        task_targets = []
        cmd_targets  = []
        match dict(doot.args.cmd.args):
            case {"target": ""|None} if not bool(doot.args.tasks):
                pass
            case {"target": ""|None}:
                task_targets +=  [tasks[x] for x in doot.args.tasks.keys()]
                cmd_targets  +=  [x for x in plugins.command if x.name == doot.args.cmd.args.target]
            case {"target": target}:
                # Print help of just the specified target(s)
                task_targets +=  [y for x,y in tasks.items() if x in target]
                cmd_targets  +=  [x for x in plugins.command if x.name == doot.args.cmd.args.target]
            case {"help": True}:
                printer.info(self.help)
                return

        logging.debug("Matched %s commands, %s tasks", len(cmd_targets), len(task_targets))
        if len(cmd_targets) == 1:
            cmd_class = cmd_targets[0].load()()
            cmd_l.info(cmd_class.help)
            if bool(doot.args.cmd.args[NON_DEFAULT_KEY]):
                self._print_current_param_assignments(cmd_class.param_specs, doot.args.cmd.args)
        elif bool(task_targets):
            for i, spec in enumerate(task_targets):
                self.print_task_spec(i, spec)
        else:
            # Print general help and list cmds
            cmd_l.info("Doot Help Command: No Target Specified/Matched")
            cmd_l.info("Available Command Targets: ")
            for x in sorted(plugins.command, key=lambda x: x.name):
                cmd_l.info("-- %s", x.name)

        cmd_l.info("\n------------------------------")
        cmd_l.info("Call a command by doing 'doot [cmd] [args]'. Eg: doot list --help")

    def print_task_spec(self, count, spec:TaskSpec):
        task_name = str(spec.name)
        match spec.ctor:
            case None:
                ctor = None
            case CodeReference():
                ctor = spec.ctor.try_import()
            case _:
                ctor = spec.ctor

        cmd_l.info("")
        cmd_l.info(LINE_SEP)
        cmd_l.info(f"{count:4}: Task: {task_name}")
        cmd_l.info(LINE_SEP)
        cmd_l.info("ver     : %s", spec.version)
        cmd_l.info("Group   : %s", spec.name.group)
        sources = "; ".join([str(x) for x in spec.sources])
        cmd_l.info("Sources : %s", sources)

        match spec.doc:
            case None:
                pass
            case str():
                cmd_l.info("")
                cmd_l.info(spec.doc)
                cmd_l.info("")
            case list() as xs:
                cmd_l.info("")
                cmd_l.info("\n".join(xs))
                cmd_l.info("")

        if ctor is not None:
            cmd_l.info("%s Ctor Class:", GROUP_INDENT)
            cmd_l.info(ctor.class_help())
            cmd_l.info(GROUP_INDENT)

        if bool(spec.extra):
            cmd_l.info("")
            cmd_l.info("%s Toml Parameters:", GROUP_INDENT)
            for kwarg,val in spec.extra:
                cmd_l.info("%s %-20s : %s", ITEM_INDENT, kwarg, val)

        if bool(spec.actions):
            cmd_l.info("")
            cmd_l.info("-- Task Actions: ")
            for action in spec.actions:
                cmd_l.info("%s %-20s : Args=%-20s Kwargs=%s", ITEM_INDENT, action.do, action.args, dict(action.kwargs) )

        cli_has_params      = task_name in doot.args.tasks
        cli_has_non_default = bool(doot.args.tasks[task_name][NON_DEFAULT_KEY])

        if cli_has_params and cli_has_non_default and ctor is not None:
            self._print_current_param_assignments(ctor.param_specs, doot.args.tasks[task_name])

    def _print_current_param_assignments(self, specs:list[ParamSpec], args:TomlGuard):
        cmd_l.info("")
        cmd_l.info("%s Current Param Assignments:", GROUP_INDENT)

        assignments = sorted([x for x in specs if not x.invisible], key=ParamSpec.key_func)
        max_param_len = 5 + ftz.reduce(max, map(len, map(lambda x: x.name, specs)), 0)
        fmt_str = f"%s %-{max_param_len}s : %s "
        for key in args[NON_DEFAULT_KEY]:
            value = args[key]
            cmd_l.info(fmt_str, ITEM_INDENT, key, value)
