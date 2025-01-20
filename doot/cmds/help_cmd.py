#!/usr/bin/env python3
"""

"""
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
from jgdv.structs.strang import CodeReference
from jgdv.cli.param_spec import ParamSpec
from jgdv.cli.arg_parser import NON_DEFAULT_KEY
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.cmds.base_cmd import BaseCommand

# ##-- end 1st party imports

# ##-- types
# isort: off
if TYPE_CHECKING:
   from jgdv import Maybe
   from jgdv.structs.chainguard import ChainGuard
   from doot.structs import TaskSpec
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
cmd_l   = doot.subprinter("cmd")
help_l  = doot.subprinter("help")
##-- end logging

LINE_SEP        : Final[str] = "------------------------------"
GROUP_INDENT    : Final[str] = "----"
ITEM_INDENT     : Final[str] = "----"

class _HelpDoot_m:

    def _doot_help(self, plugins) -> list[str]:
        result = []
        # Print general help and list cmds
        result.append("Doot Help Command: No Target Specified/Matched")
        result.append("Available Command Targets: ")
        for x in sorted(plugins.command, key=lambda x: x.name):
            result.append("-- %s" % x.name)
        else:
            result.append("\n------------------------------")
            result.append("Call a command by doing 'doot [cmd] [args]'. Eg: doot list --help")
            return result

class _HelpCmd_m:

    def _cmd_help(self, cmd) -> list[str]:
        result = []
        cmd_class    = cmd.load()
        cmd_instance = cmd_class()
        result += cmd_instance.help
        result += self._print_current_param_assignments(cmd_instance.param_specs, doot.args.cmd)
        return result

class _HelpTask_m:

    def _task_help(self, count, spec:TaskSpec) -> list[str]:
        """ Print the help for a task spec """
        task_name = str(spec.name)
        result = [
            "",
            LINE_SEP,
            f"{count:4}: Task: {task_name}",
            LINE_SEP,
        ]
        match spec.ctor:
            case None:
                ctor = None
            case CodeReference():
                ctor = spec.ctor()
            case _:
                ctor = spec.ctor

        result.append("ver     : {spec.version}")
        result.append("Group   : {spec.name[0:]}")
        sources = "; ".join([str(x) for x in spec.sources])
        result.append("Sources : {sources}")

        match spec.doc:
            case None:
                pass
            case str() as x:
                result += [None, x, None]
            case [*xs]:
                result.append(None)
                result += xs
                result.append(None)

        if ctor is not None:
            result.append("{GROUP_INDENT} Ctor Class:")
            result += ctor.class_help()
            result.append(GROUP_INDENT)

        if bool(spec.extra):
            result.append(None)
            result.append(f"{GROUP_INDENT} Toml Parameters:")
            for kwarg,val in spec.extra.items():
                result.append("%s %-20s : %s" % ITEM_INDENT, kwarg, val)

        if bool(spec.actions):
            result.append(None)
            result.append("-- Task Actions: ")
            sub_indent = (1 + len(ITEM_INDENT)) * " "
            for action in spec.actions:
                result.append("%s %-30s:" % ITEM_INDENT, action.do)
                result.append("%sArgs=%-20s" % sub_indent, action.args)
                result.append("%sKwargs=%s" % sub_indent, dict(action.kwargs))

        cli_has_params      = task_name in doot.args.sub
        cli_has_non_default = NON_DEFAULT_KEY in doot.args.sub[task_name] and bool(doot.args.sub[task_name][NON_DEFAULT_KEY])

        if cli_has_params and cli_has_non_default and ctor is not None:
            self._print_current_param_assignments(ctor.param_specs, doot.args.sub[task_name])



class HelpCmd(_HelpDoot_m, _HelpCmd_m, _HelpTask_m, BaseCommand):
    _name      = "help"
    _help      = ["Print info about the specified cmd or task",
                  "Can also be triggered by passing --help to any command or task"
                  ]

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            self.build_param(prefix=1, name="target", type=str, default="", desc="The target to get help about. A command or task.")
            ]

    def __call__(self, tasks, plugins):
        """List task generators"""
        task_targets = []
        cmd_targets  = []
        self_help    = False
        match dict(doot.args.cmd.args):
            case {"target": ""|None} if bool(doot.args.sub):
                task_targets += [tasks[x] for x in doot.args.sub.keys()]
            case {"target": ""|None} | {"help":True}:
                self_help = True
            case {"target": x} if x in doot.cmd_aliases:
                aliased = doot.cmd_aliases[x][0]
                cmd_targets  +=  [x for x in plugins.command if x.name == aliased]
            case {"target": target}:
                # Print help of just the specified target(s)
                task_targets +=  [y for x,y in tasks.items() if x in target]
                cmd_targets  +=  [x for x in plugins.command if x.name == doot.args.cmd.args.target]
            case {"target": target}:
                # Print help of just the specified target(s)
                task_targets +=  [y for x,y in tasks.items() if x in target]
                cmd_targets  +=  [x for x in plugins.command if x.name == doot.args.cmd.args.target]
            case {"help": True}:
                self_help = True


        logging.debug("Matched %s commands, %s tasks", len(cmd_targets), len(task_targets))
        match cmd_targets:
            case []:
                pass
            case [x]:
                result = self._cmd_help(x)
                self._print_text(result)
                return
            case [*xs]:
                cmd_l.error("To print help for a command, choose 1 command at a time")
                return

        match task_targets:
            case []:
                pass
            case [*xs]:
                result = []
                for i, spec in enumerate(task_targets):
                    result += self._task_help(i, spec)
                else:
                    self._print_text(result)
                    return

        match self_help:
            case True:
                result = self._self_help()
                self._print_text(result)
            case False:
                result = self._doot_help(plugins)
                self._print_text(result)

    def _self_help(self) -> list:
        return self.help


    def _print_current_param_assignments(self, specs:list[ParamSpec], args:dict|ChainGuard) -> list[str]:
        if args[NON_DEFAULT_KEY] is None:
            return []
        result = []
        result.append(None)
        result.append("%s Current Param Assignments:" % GROUP_INDENT)

        assignments   = sorted([x for x in specs], key=ParamSpec.key_func)
        max_param_len = 5 + ftz.reduce(max, map(len, map(lambda x: x.name, specs)), 0)
        fmt_str       = f"%s %-{max_param_len}s : %s "
        relevant_args = args.args
        if "args" in relevant_args:
            relevant_args = relevant_args['args']


        for key in args[NON_DEFAULT_KEY]:
            if key == "help":
                continue
            match relevant_args[key]:
                case None:
                    pass
                case x:
                    result.append(fmt_str % (ITEM_INDENT, key, x))
        else:
            result.append(None)
            return result
