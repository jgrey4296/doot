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
from collections import ChainMap
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
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import ArgParser_i
from doot.structs import ParamSpec, TaskSpec, TaskName

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

PARAM_ASSIGN_PREFIX : Final[str]  = doot.constants.patterns.PARAM_ASSIGN_PREFIX
NON_DEFAULT_KEY     : Final[str]  = doot.constants.misc.NON_DEFAULT_KEY
SEP                 : Final[str]  = doot.constants.patterns.TASK_PARSE_SEP
DEFAULT_CLI_CMD     : Final[str]  = doot.constants.misc.DEFAULT_CLI_CMD
EMPTY_CLI_CMD       : Final[str]  = doot.constants.misc.EMPTY_CLI_CMD

default_task        : Final[str]  = doot.config.on_fail((None,)).settings.tasks.default_task(wrapper=TaskName.build)
default_cmd         : Final[str]  = doot.config.on_fail(DEFAULT_CLI_CMD, str).settings.general.default_cmd()
empty_cmd           : Final[str]  = doot.config.on_fail(EMPTY_CLI_CMD, str).settings.general.empty_cmd()

class DootFlexibleParser(ArgParser_i):
    """
    convert argv to tomlguard by:
    parsing each arg as toml,

    # doot {args} {cmd} {cmd_args}
    # doot {args} [{task} {tasks_args}] - implicit do cmd
    """

    class _ParseState(enum.Enum):
        HEAD  = enum.auto()
        CMD   = enum.auto()
        TASK  = enum.auto()
        EXTRA = enum.auto()

    def __init__(self):
        self.PS               = DootFlexibleParser._ParseState
        self.head_arg_specs   = None
        self.registered_cmds  = None
        self.registered_tasks = None
        self.default_help     = ParamSpec(name="help", default=False, prefix="--")

        ## -- results
        self.head_call                          = None
        self.head_args                          = None
        self.cmd_name                           = None
        self.cmd_args                           = {}
        self.tasks_args                         = []
        self.extras                             = {}
        self.force_help                         = False

        ## -- loop state
        self.focus                             = self.PS.HEAD

    def _build_defaults_dict(self, param_specs:list) -> dict:
        return { x.name : x.default for x in param_specs }

    def parse(self, args:list, *, doot_specs:list[ParamSpec], cmds:TomlGuard, tasks:TomlGuard) -> None|TomlGuard:
        """
          Parses the list of arguments against available registered parameter specs, cmds, and tasks.
        """
        logging.debug("Parsing args: %s", args)
        self.registered_cmds  : dict[str, Command_i]                      = cmds
        self.registered_tasks : dict[TaskName, TaskSpec]                  = tasks
        self.head_call                                                    = args[0]
        self.head_args                                                    = self._build_defaults_dict(doot_specs)
        self.head_arg_specs                                               = doot_specs
        self.focus                                                        = self.PS.HEAD

        remaining                                                         = args[1:]

        from jgdv.util.time_ctx import TimeCtx
        with TimeCtx(logger=logging, entry_msg="--- CLI Arg Parsing Start", exit_msg="---- CLI Arg Parsing Took", level=20):
            while bool(remaining):
                match self.focus:
                    case self.PS.HEAD:
                        remaining = self.process_head(remaining)
                        self.focus = self.PS.CMD
                    case self.PS.CMD:
                        remaining = self.process_cmd(remaining)
                        self.focus = self.PS.TASK
                    case self.PS.TASK:
                        remaining = self.process_task(remaining)
                        self.focus = self.PS.EXTRA
                    case self.PS.EXTRA:
                        remaining = self.process_extra(remaining)

        if not bool(self.cmd_args) and empty_cmd in self.registered_cmds:
            # Default to the empty cmd
            self.cmd_name = empty_cmd
            self.cmd_args = self._build_defaults_dict(self.registered_cmds[empty_cmd].param_specs)

        # Retarget if '--help' has been set to true
        if self.cmd_args.get('help', False) is True:
            self.cmd_args['target']      = self.cmd_name
            self.cmd_name                = "help"
        elif any(x[1].get('help', False) is True for x in self.tasks_args if (target:=x[0])):
            self.cmd_args['target'] = target
            self.cmd_name = "help"

        # TODO ensure duplicated tasks have different args
        data = {
            "head"   : {"name": self.head_call, "args": self.head_args },
            "cmd"    : {"name" : self.cmd_name, "args" : self.cmd_args },
            "tasks"  : { name : args for name,args in self.tasks_args  },
            "extras" : self.extras
            }
        return TomlGuard(data)

    def process_head(self, args) -> list[str]:
        """ consume arguments for doot actual """
        logging.debug("Head Parsing: %s", args)
        head = args[0]
        while bool(args) and args[0] not in self.registered_cmds and args[0] not in self.registered_tasks:
            match [x for x in self.head_arg_specs if x == args[0]]:
                case []:
                    raise doot.errors.DootParseError("Unrecognized head arg", args[0])
                case [x]:
                    x.maybe_consume(args, self.head_args)
                case [*xs]:
                    raise doot.errors.DootParseError("Multiple possible head args", args[0])

        return args

    def process_cmd(self, args) -> list[str]:
        """ consume arguments for the command being run """
        logging.debug("Cmd Parsing: %s", args)
        head                     = args[0]
        cmd                      = self.registered_cmds.get(head, None)
        self.cmd_name            = head
        if cmd is None:
            cmd                      = self.registered_cmds[default_cmd]
            self.cmd_name            = default_cmd
            current_specs            = list(sorted(cmd.param_specs, key=ParamSpec.key_func))
            self.cmd_args            = self._build_defaults_dict(current_specs)
            return args

        current_specs            = list(sorted(cmd.param_specs, key=ParamSpec.key_func))
        self.cmd_args            = self._build_defaults_dict(current_specs)

        args.pop(0)
        while bool(args) and args[0] not in self.registered_tasks:
            if args[0] == SEP: # hit SEP, the forced separator
                # eg: doot list a b c -- something else
                args.pop(0)
                break
            match [x for x in current_specs if x == args[0]]:
                case []:
                    raise doot.errors.DootParseError("Unrecognized cmd arg", head, args[0])
                case [x]:
                    x.maybe_consume(args, self.cmd_args)
                case [*xs] if all(y.positional for y in xs):
                    self._consume_next_positional(args, self.cmd_args, xs)
                case [*xs] if len(list(y for y in xs if not y.positional)):
                    raise doot.errors.DootParseError("Multiple possible cmd args", head, args[0])

        self.cmd_args[NON_DEFAULT_KEY] = self._calc_non_default(self._build_defaults_dict(current_specs), self.cmd_args)
        return args

    def process_task(self, args) -> list[str]:
        """ consume arguments for tasks """
        logging.debug("Task Parsing: %s", args)
        if args[0] not in self.registered_tasks:
            if default_task is None:
                return args
            task                     = self.registered_tasks[default_task]
            assert(isinstance(task, TaskSpec))
            task_name                 = default_task
            spec_params               = [ParamSpec.build(x) for x in task.extra.on_fail([], list).cli()]
            ctor_params               = task.ctor.try_import().param_specs
            current_specs             = list(sorted(spec_params + ctor_params, key=ParamSpec.key_func))
            task_args                 = self._build_defaults_dict(current_specs)
            task_args[NON_DEFAULT_KEY] = []
            self.tasks_args.append((task_name, task_args))
            return args

        while bool(args) and args[0] in self.registered_tasks:
            task_name                 = args.pop(0)
            task                      = self.registered_tasks[task_name]
            assert(isinstance(task, TaskSpec))
            spec_params               = [ParamSpec.build(x) for x in task.extra.on_fail([], list).cli()]
            ctor_params               = task.ctor.try_import().param_specs
            current_specs             = list(sorted(spec_params + ctor_params, key=ParamSpec.key_func))
            task_args                 = self._build_defaults_dict(current_specs)

            default_args              = task_args.copy()
            logging.debug("Parsing Task args for: %s: Available: %s", task_name, task_args.keys())

            while bool(args) and args[0] not in self.registered_tasks:
                if args[0] == SEP:
                    args.pop(0)
                    break

                match [x for x in current_specs if x == args[0]]:
                    case [] if args[0].startswith(PARAM_ASSIGN_PREFIX):
                        # No matches, its a free cli arg.
                        try:
                            key, value = args[0].split("=")
                            task_args[key.removeprefix("--")] = value
                            args.pop(0)
                        except ValueError:
                            raise doot.errors.DootParseError("Arg failed to split into key=value", args[0])
                    case [x] if not x.positional:
                        x.maybe_consume(args, task_args)
                    case [*xs] if all(y.positional for y in xs):
                        self._consume_next_positional(args, task_args, xs)
                    case [*xs]:
                        raise doot.errors.DootParseError("Multiple possible task args", task_name, args[0])

            if task_name in [x[0] for x in self.tasks_args]:
                raise doot.errors.DootParseError("a single task was specified twice")

            task_args[NON_DEFAULT_KEY] = self._calc_non_default(default_args, task_args)
            logging.debug("Resulting Arg Assignments for %s : %s", task_name, task_args)
            self.tasks_args.append((task_name, task_args))

        return args

    def process_extra(self, args) -> None:
        logging.debug("Extra Parsing: %s", args)
        return None

    def _consume_next_positional(self, args, arg_dict, params:list):
        """
          try each positional param until success
        """
        for param in params:
            try:
                if 1 <= param.maybe_consume(args, arg_dict):
                    return
            except doot.errors.DootParseResetError:
                continue

        raise doot.errors.DootParseError("No positional argument succeeded", args)

    def _calc_non_default(self, defaults, actual) -> list:
        return [x for x,y in actual.items() if x not in defaults or defaults[x] != y]
