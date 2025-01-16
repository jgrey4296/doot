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
from jgdv.structs.strang import CodeReference
from jgdv.cli.param_spec import ParamSpec
from jgdv.cli.arg_parser import NON_DEFAULT_KEY
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.cmds.base_cmd import BaseCommand

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
cmd_l   = doot.subprinter("cmd")
help_l  = doot.subprinter("help")
##-- end logging

LINE_SEP        : Final[str] = "------------------------------"
GROUP_INDENT    : Final[str] = "----"
ITEM_INDENT     : Final[str] = "----"

class HelpCmd(BaseCommand):
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
        match dict(doot.args.cmd.args):
            case {"target": ""|None} if bool(doot.args.sub):
                task_targets += [tasks[x] for x in doot.args.sub.keys()]
            case {"target": ""|None} | {"help":True}:
                help_l.user(self.help)
                return
            case {"target": target}:
                # Print help of just the specified target(s)
                task_targets +=  [y for x,y in tasks.items() if x in target]
                cmd_targets  +=  [x for x in plugins.command if x.name == doot.args.cmd.args.target]
            case {"help": True}:
                help_l.user(self.help)
                return

        logging.debug("Matched %s commands, %s tasks", len(cmd_targets), len(task_targets))
        if len(cmd_targets) == 1:
            cmd_class = cmd_targets[0].load()()
            cmd_l.user(cmd_class.help)
            if bool(doot.args.cmd.get(NON_DEFAULT_KEY, None)):
                self._print_current_param_assignments(cmd_class.param_specs, doot.args.cmd)
        elif bool(task_targets):
            for i, spec in enumerate(task_targets):
                self.print_task_spec(i, spec)
        else:
            # Print general help and list cmds
            cmd_l.user("Doot Help Command: No Target Specified/Matched")
            cmd_l.user("Available Command Targets: ")
            for x in sorted(plugins.command, key=lambda x: x.name):
                cmd_l.info("-- %s", x.name)

        cmd_l.user("\n------------------------------")
        cmd_l.user("Call a command by doing 'doot [cmd] [args]'. Eg: doot list --help")

    def print_task_spec(self, count, spec:TaskSpec):
        """ Print the help for a task spec """
        task_name = str(spec.name)
        match spec.ctor:
            case None:
                ctor = None
            case CodeReference():
                ctor = spec.ctor()
            case _:
                ctor = spec.ctor

        cmd_l.user("")
        cmd_l.user(LINE_SEP)
        cmd_l.user(f"{count:4}: Task: {task_name}")
        cmd_l.user(LINE_SEP)
        cmd_l.user("ver     : %s", spec.version)
        cmd_l.user("Group   : %s", spec.name[0:])
        sources = "; ".join([str(x) for x in spec.sources])
        cmd_l.user("Sources : %s", sources)

        match spec.doc:
            case None:
                pass
            case str():
                cmd_l.user("")
                cmd_l.user(spec.doc)
                cmd_l.user("")
            case list() as xs:
                cmd_l.user("")
                cmd_l.user("\n".join(xs))
                cmd_l.user("")

        if ctor is not None:
            cmd_l.user("%s Ctor Class:", GROUP_INDENT)
            cmd_l.user(ctor.class_help())
            cmd_l.user(GROUP_INDENT)

        if bool(spec.extra):
            cmd_l.user("")
            cmd_l.user("%s Toml Parameters:", GROUP_INDENT)
            for kwarg,val in spec.extra.items():
                cmd_l.user("%s %-20s : %s", ITEM_INDENT, kwarg, val)

        if bool(spec.actions):
            cmd_l.user("")
            cmd_l.user("-- Task Actions: ")
            sub_indent = (1 + len(ITEM_INDENT)) * " "
            for action in spec.actions:
                cmd_l.user("%s %-30s:",    ITEM_INDENT, action.do)
                cmd_l.user("%sArgs=%-20s", sub_indent, action.args)
                cmd_l.user("%sKwargs=%s",  sub_indent, dict(action.kwargs))

        cli_has_params      = task_name in doot.args.sub
        cli_has_non_default = NON_DEFAULT_KEY in doot.args.sub[task_name] and bool(doot.args.sub[task_name][NON_DEFAULT_KEY])

        if cli_has_params and cli_has_non_default and ctor is not None:
            self._print_current_param_assignments(ctor.param_specs, doot.args.sub[task_name])

    def _print_current_param_assignments(self, specs:list[ParamSpec], args:dict|ChainGuard):
        cmd_l.user("")
        cmd_l.user("%s Current Param Assignments:", GROUP_INDENT)

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
                    cmd_l.user(fmt_str, ITEM_INDENT, key, x)
