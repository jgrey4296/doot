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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto, Mixin
from jgdv.structs.strang import CodeReference
from jgdv.cli.param_spec import ParamSpec
from jgdv.cli._interface import NON_DEFAULT_KEY
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.cmds.core.cmd import BaseCommand
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
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from jgdv.structs.chainguard import ChainGuard
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from doot.structs import TaskSpec
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

LINE_SEP        : Final[str] = "------------------------------"
GROUP_INDENT    : Final[str] = "----"
ITEM_INDENT     : Final[str] = "-"

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
        # result += self._cmd_param_assignments(cmd_instance)
        return result


    def _cmd_param_assignments(self, cmd) -> list[str]:
        result = []
        result.append(None)
        result.append("%s Parameters:" % GROUP_INDENT)

        max_param_len = 5 + ftz.reduce(max, map(len, map(lambda x: x.name, cmd.param_specs)), 0)
        fmt_str       = f"> %{max_param_len}s : (%-5s) : %s "
        args = doot.args.cmd.args
        last_prefix = None
        for param in sorted([x for x in cmd.param_specs], key=ParamSpec.key_func):
            if last_prefix and last_prefix != param.prefix:
                result.append(None)
            last_prefix = param.prefix
            match param.type_:
                case type() as x:
                    type_ = x.__name__
                case x:
                    type_ = x
            match args.get(param.name, None):
                case _ if param.name == "help":
                    pass
                case None:
                    result.append(fmt_str % (param.key_str, type_, f"default: {param.default}"))
                case val if val == param.default:
                    result.append(fmt_str % (param.key_str, type_, f"default: {val}"))
                case val:
                    result.append(fmt_str % (param.key_str, type_, val))
        else:
            result.append(None)
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
            f"ver     : {spec.version}",
            f"Group   : {spec.name[0:]}",
            ]

        sources = "; ".join([str(x) for x in spec.sources])
        result.append(f"Sources : {sources}")

        match spec.doc:
            case None:
                pass
            case str() as x:
                result += [None, x, None]
            case [*xs]:
                result.append(None)
                result += xs
                result.append(None)

        match spec.ctor:
            case None:
                ctor = None
            case CodeReference():
                ctor = spec.ctor()
            case _:
                ctor = spec.ctor

        if ctor is not None:
            result.append(f"{GROUP_INDENT} Ctor Class:")
            result += ctor.class_help()
            result.append(None)

        extra_keys = set(spec.extra.keys()) - {"cli"}
        if bool(extra_keys):
            result.append(None)
            result.append(f"{GROUP_INDENT} Toml Parameters:")
            for kwarg,val in spec.extra.items():
                if kwarg == "cli":
                    continue
                result.append("%s %-20s : %s" % (ITEM_INDENT, kwarg, val))
            result.append(None)

        if bool(spec.actions):
            result.append("%s Task Actions: " % GROUP_INDENT)
            sub_indent = (1 + len(ITEM_INDENT)) * " "
            for action in spec.actions:
                result.append("%s %-30s:" % (ITEM_INDENT, action.do))
                result.append("%sArgs=%-20s" % (sub_indent, action.args))
                result.append("%sKwargs=%s" % (sub_indent, dict(action.kwargs)))


        result += self._task_param_assignments(spec)

        return result

    def _task_param_assignments(self, spec:TaskSpec) -> list:
        if not bool(spec.param_specs):
            return []

        result = []
        result.append(None)
        result.append("%s Parameters:" % GROUP_INDENT)

        max_param_len = 5 + ftz.reduce(max, map(len, map(lambda x: x.key_str, spec.param_specs)), 0)
        fmt_str       = f"> %{max_param_len}s : (%5s) : %s "
        args          = doot.args.sub[spec.name]
        last_prefix   = None
        for param in sorted([x for x in spec.param_specs], key=ParamSpec.key_func):
            if last_prefix and last_prefix != param.prefix:
                result.append(None)
            match param.type_:
                case type() as x:
                    type_ = x.__name__
                case x:
                    type_ = x
            match args.get(param.name, None):
                case _ if param.name == "help":
                    pass
                case None:
                    result.append(fmt_str % (param.key_str, type_, f"default: {param.default}"))
                case val if val == param.default:
                    result.append(fmt_str % (param.key_str, type_, f"default: {val}"))
                case val:
                    result.append(fmt_str % (param.key_str, type_, val))
        else:
            result.append(None)
            return result


##--|
@Proto(Command_p)
@Mixin(_HelpDoot_m, _HelpCmd_m, _HelpTask_m)
class HelpCmd(BaseCommand):
    _name      = "help"
    _help      = ["Print info about the specified cmd or task",
                  "Can also be triggered by passing --help to any command or task"
                  ]

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(name="<1>target", type=str, default="", desc="The target to get help about. A command or task.")
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
        doot.report.active_level(logmod.INFO)
        match cmd_targets:
            case []:
                pass
            case [x]:
                result = self._cmd_help(x)
                self._print_text(result)
                return
            case [*xs]:
                doot.report.error("To print help for a command, choose 1 command at a time")
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
