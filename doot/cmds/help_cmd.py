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
from ._base import BaseCommand
from ._interface import Command_p
from doot.workflow._interface import Task_p

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
    from jgdv import Maybe
    from jgdv.structs.chainguard import ChainGuard
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from doot.workflow._interface import TaskSpec_i

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

LINE_SEP        : Final[str] = "------------------------------"
GROUP_INDENT    : Final[str] = "----"
ITEM_INDENT     : Final[str] = "-"

class _HelpDoot_m:

    def _doot_help(self, plugins:ChainGuard) -> list[str]:
        result = []
        # Print general help and list cmds
        result.append("Doot Help Command: No Target Specified/Matched")
        result.append("Available Command Targets: ")
        for x in sorted(plugins.command, key=lambda x: x.name):
            result.append(f"-- {x.name}")
        else:
            result.append("\n------------------------------")
            result.append("Call a command by doing 'doot [cmd] [args]'. Eg: doot list --help")
            return result

class _HelpCmd_m:

    def _cmd_help(self, *, idx:int, cmd:Any) -> list[str]:
        result        = []
        cmd_class     = cmd.load()
        cmd_instance  = cmd_class()
        result += cmd_instance.help
        return result


    def _cmd_param_assignments(self, idx:int, cmd:Any) -> list[Maybe[str]]:
        result : list[Maybe[str]] = []
        result.append(None)
        result.append(f"{GROUP_INDENT} Parameters:")

        max_param_len  = 5 + ftz.reduce(max, map(len, (x.name for x in cmd.param_specs())), 0)
        fmt_str        = f"> %{max_param_len}s  : (%-5s) : %s "
        args           = doot.args.cmds[self.name][idx].args # type: ignore[attr-defined]
        last_prefix    = None
        for param in sorted(cmd.param_specs(), key=ParamSpec.key_func):
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

    def _task_help(self, count:int, spec:TaskSpec_i) -> list[Maybe[str]]:
        """ Print the help for a task spec """
        result     : list[Maybe[str]]
        task_name  : str
        ctor       : Maybe[Task_p|type[Task_p]]
        ##--|
        task_name = str(spec.name)
        result = [
            "",
            LINE_SEP,
            f"{count:4}: Task: {task_name}",
            LINE_SEP,
            f"ver     : {spec.version}",
            f"Group   : {spec.name[0,:]}",
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
                ctor = spec.ctor(raise_error=True)
            case _:
                ctor = spec.ctor

        assert(isinstance(ctor, Task_p))
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
                result.append(f"{ITEM_INDENT} {kwarg:-20} : {val}")
            result.append(None)

        if bool(spec.actions):
            result.append(f"{GROUP_INDENT} Task Actions: ")
            sub_indent = (1 + len(ITEM_INDENT)) * " "
            for action in spec.actions:
                result.append(f"{ITEM_INDENT} {action.do:-30}:")

        result += self._task_param_assignments(spec)

        return result

    def _task_param_assignments(self, spec:TaskSpec_i) -> list:
        result : list[Maybe[str]]
        ##--|
        if not bool(spec.param_specs()):
            return []

        result = []
        result.append(None)
        result.append(f"{GROUP_INDENT} Parameters:")

        max_param_len = 5 + ftz.reduce(max, map(len, (x.key_str for x in spec.param_specs())), 0)
        fmt_str       = f"> %{max_param_len}s : (%5s) : %s "
        args          = doot.args.subs[spec.name]
        last_prefix   = None
        for param in sorted(spec.param_specs(), key=ParamSpec.key_func):
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
    _help      = ("Print info about the specified cmd or task",
                  "Can also be triggered by passing --help to any command or task",
                  )

    @override
    def param_specs(self) -> list:
        return [
            *super().param_specs(),
            self.build_param(name="<1>target", type=str, default="", desc="The target to get help about. A command or task."),
        ]

    def __call__(self, *, idx:int, tasks:ChainGuard, plugins:ChainGuard):  # noqa: PLR0912
        """List task generators"""
        task_targets  : list
        cmd_targets   : list
        self_help     : bool
        ##--|
        task_targets = []
        cmd_targets  = []
        self_help    = False
        match dict(doot.args.cmds[self.name][idx].args[self.name][idx]):
            case {"target": ""|None} if bool(doot.args.subs):
                # No target, generate list of all tasks
                task_targets += [tasks[x] for x in doot.args.subs.keys()]
            case {"target": ""|None} | {"help":True}:
                self_help = True
            case {"target": x} if x in doot.cmd_aliases:
                aliased = doot.cmd_aliases[x][0]
                cmd_targets  +=  [x for x in plugins.command if x.name == aliased]
            case {"target": target}:
                # Print help of just the specified target(s)
                task_targets +=  [y for x,y in tasks.items() if x in target]
                cmd_targets  +=  [x for x in plugins.command if x.name == target]
            case {"help": True}:
                self_help = True


        logging.debug("Matched %s commands, %s tasks", len(cmd_targets), len(task_targets))
        doot.report.active_level(logmod.INFO)
        match cmd_targets:
            case []:
                pass
            case [x]:
                result = self._cmd_help(idx=idx, cmd=x) # type: ignore[attr-defined]
                self._print_text(result)
                return
            case [*xs]:
                doot.report.gen.error("To print help for a command, choose 1 command at a time")
                return

        match task_targets:
            case []:
                pass
            case [*xs]:
                result = []
                for i, spec in enumerate(task_targets):
                    result += self._task_help(i, spec) # type: ignore[attr-defined]
                else:
                    self._print_text(result)
                    return

        match self_help:
            case True:
                result = self.help
                self._print_text(result)
            case False:
                result = self._doot_help(plugins) # type: ignore[attr-defined]
                self._print_text(result)
