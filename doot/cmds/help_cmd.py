#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

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
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
# from uuid import UUID, uuid1
# from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

import doot
from doot.structs import DootParamSpec, DootTaskSpec, DootCodeReference
from doot._abstract import Command_i
from doot.constants import NON_DEFAULT_KEY
from collections import defaultdict


class HelpCmd(Command_i):
    _name      = "help"
    _help      = ["Print info about the specified cmd or task",
                  "Can also be triggered by passing --help to any command or task"
                  ]

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            # self.make_param(name="target", type=str, default=""),
            self.make_param(name="target", type=str, positional=True, default="", desc="The target to get help about. A command or task.")
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
                task_targets +=  [y for x,y in tasks.items() if target in x ]
                cmd_targets  +=  [x for x in plugins.command if x.name == doot.args.cmd.args.target]
            case {"help": True}:
                printer.info(self.help)
                return


        logging.debug("Matched %s commands, %s tasks", len(cmd_targets), len(task_targets))
        if len(cmd_targets) == 1:
            cmd_class = cmd_targets[0].load()()
            printer.info(cmd_class.help)
            if bool(doot.args.cmd[NON_DEFAULT_KEY]):
                self._print_current_param_assignments(cmd_class.param_specs, doot.args.cmd.args)


        elif bool(task_targets):
            for i, spec in enumerate(task_targets):
                self.print_task_spec(i, spec)

        else:
            # Print general help and list cmds
            printer.info("Doot Help Command: No Target Specified/Matched")
            printer.info("Available Command Targets: ")
            for x in sorted(plugins.command, key=lambda x: x.name):
                printer.info("-- %s", x.name)

        printer.info("\n------------------------------")
        printer.info("Call a command by doing 'doot [cmd] [args]'. Eg: doot list --help")


    def print_task_spec(self, count, spec:DootTaskSpec):
        task_name = spec.name
        match spec.ctor:
            case None:
                ctor = None
            case DootCodeReference():
                ctor = spec.ctor.try_import()
            case _:
                ctor = spec.ctor

        lines     = []
        lines.append("")
        lines.append("------------------------------")
        lines.append(f"{count:4}: Task: {task_name}")
        lines.append("------------------------------")
        lines.append(f"ver    : {spec.version}")
        lines.append(f"Group  : {spec.name.group}")
        lines.append(f"Source : {spec.source}")

        if ctor is not None:
            lines.append(ctor.class_help())


        match spec.doc:
            case None:
                pass
            case str():
                lines.append("")
                lines.append(f"--   {spec.doc}")
            case list() as xs:
                lines.append("")
                lines.append("--  " + "\n--  ".join(xs))

        printer.info("\n".join(lines))

        if bool(spec.extra):
            printer.info("")
            printer.info("Toml Parameters:")
            for kwarg,val in spec.extra:
                printer.info("-- %-20s : %s", kwarg, val)

        if bool(spec.actions):
            printer.info("")
            printer.info("Task Actions: ")
            for action in spec.actions:
                printer.info("-- %-20s : Args=%-20s Kwargs=%s", action.do, action.args, dict(action.kwargs) )


        cli_has_params = str(task_name) in doot.args.tasks
        cli_has_non_default = bool(doot.args.tasks[str(task_name)][NON_DEFAULT_KEY])

        if cli_has_params and cli_has_non_default and ctor is not None:
            self._print_current_param_assignments(ctor.param_specs, doot.args.tasks[task_name])

    def _print_current_param_assignments(self, specs:list[DootParamSpec], args:TomlGuard):
        if not bool(specs):
            return

        printer.info("")
        printer.info("Current Param Assignments:")
        results = []
        max_param_len = 5 + ftz.reduce(max, map(len, map(lambda x: x.name, specs)), 0)
        fmt_str = f"%-{max_param_len}s %s : %s"
        for spec in sorted(specs, key=DootParamSpec.key_func):
            if spec.invisible:
                continue
            value = args._table().get(spec.name, spec.default)
            is_default = "   " if value == spec.default else "(*)"
            printer.info(fmt_str, spec.name, is_default, value)
