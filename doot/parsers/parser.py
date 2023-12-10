##-- imports
from __future__ import annotations

# import abc
# import datetime
import enum
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
##-- end logging

import tomlguard
import doot
from doot._abstract import ArgParser_i
from doot.structs import DootParamSpec
from collections import ChainMap

@doot.check_protocol
class DootArgParser(ArgParser_i):
    """
    convert argv to tomlguard by:
    parsing each arg as toml,

    # doot {args} {cmd} {cmd_args}
    # doot {args} [{task} {task_args}] - implicit do cmd
    """

    class _ParseState(enum.Enum):
        HEAD = enum.auto()
        CMD  = enum.auto()
        TASK = enum.auto()

    def _build_defaults_dict(self, param_specs:list) -> dict:
        return { x.name : x.default for x in param_specs }

    def parse(self, args:list, *, doot_specs:list[DootParamSpec], cmds:TomlGuard, tasks:TomlGuard) -> None|TomlGuard:
        """
          Parses the list of arguments against available registered parameter specs, cmds, and tasks.
        """
        logging.debug("Parsing args: %s", args)
        head_arg     = args[0]

        PS = DootArgParser._ParseState
        ##-- results
        doot_args       = self._build_defaults_dict(doot_specs)
        cmd             = None
        cmd_name        = None
        cmd_args        = {}
        mentioned_tasks = []
        task_args       = []
        ##-- end results

        ##-- loop state
        declared_cmds        = set(cmds.keys())
        declared_tasks       = set(tasks.keys())
        current_specs        = doot_specs
        focus                = PS.HEAD
        force_help           = False
        non_default_cmd_arg  = False
        non_default_task_arg = False
        ##-- end loop state

        # Help is special, it overrides the cmd if its specified anywhere

        default_help = DootParamSpec(name="help", default=False, prefix="--")

        logging.info("Initial Arg Specs: %s", current_specs)
        # loop through args as a state machine.
        # starts in "doot" state, progresses to "cmd" then "task" before quitting
        for arg in args[1:]:
            matching_specs       = [x for x in current_specs if x == arg]
            positional_remain    = bool([x for x in matching_specs if x.positional])
            logging.info("Handling: %s, State: %s, Specs: %s", arg, focus, matching_specs)

            if len(matching_specs) > 1 and len(set([x.short for x in matching_specs])) == 1:
                raise doot.errors.DootParseError("Multiple matching arg specs, use it's full name", arg, [x.name for x in matching_specs])

            match focus:
                case PS.HEAD if arg in declared_cmds:
                    logging.info("Switching to CMD context: %s", arg)
                    focus          = PS.CMD
                    cmd            = cmds[arg]
                    current_specs  = list(sorted(cmd.param_specs, key=DootParamSpec.key_func))
                    logging.info("Updated Specs to: %s", current_specs)
                    matching_specs = []
                    cmd_name       = arg
                    cmd_args       = self._build_defaults_dict(current_specs)
                case PS.CMD | PS.TASK if arg == default_help:
                    logging.info("Forcing HELP cmd")
                    force_help = True
                case _ if arg in declared_tasks and not positional_remain:
                    logging.info("Switching to TASK context: %s", arg)
                    # handle switching to task context
                    focus          = PS.TASK
                    mentioned_tasks.append(arg)
                    current_specs  = list(sorted(tasks[arg].ctor.param_specs, key=DootParamSpec.key_func))
                    logging.info("Updated Specs to: %s", current_specs)

                    matching_specs = []
                    new_task_args  = self._build_defaults_dict(current_specs)
                    task_args.append(new_task_args)
                ##-- handle args for specific context
                case PS.HEAD if bool(matching_specs):
                    spec = matching_specs[0]
                    logging.info("Setting HEAD : arg(%s) = %s", spec.name, arg)
                    spec.add_value_to(doot_args, arg)
                case PS.CMD if bool(matching_specs):
                    spec = matching_specs[0]
                    logging.info("Setting Cmd(%s): arg(%s) = %s", cmd_name, spec.name, arg)
                    non_default_cmd_arg |= spec.add_value_to(cmd_args, arg)
                case PS.TASK if bool(matching_specs):
                    spec = matching_specs[0]
                    logging.info("Setting Task(%s) : arg(%s) = %s", mentioned_tasks[-1],spec.name, arg)
                    non_default_task_arg |= spec.add_value_to(task_args[-1], arg)
                ##-- end handle args for specific context
                case _ if not (bool(doot_specs) or bool(cmds) or bool(tasks)):
                    pass
                case _:
                    raise doot.errors.DootParseError("Unrecognized {} Parameter: {}. Available Parameters: {}".format(focus.name, arg, [repr(x) for x in current_specs]))

            if bool(matching_specs) and not matching_specs[0].repeatable:
                current_specs.remove(matching_specs[0])

        if force_help:
            cmd_args['target'] = cmd_name
            cmd_name = "help"

        # TODO ensure duplicated tasks have different args
        data = {
            "head" : {"name": head_arg,
                      "args": doot_args },
            "cmd" : {"name" : cmd_name or doot.constants.DEFAULT_CLI_CMD,
                     "args" : cmd_args },
            "tasks" : {name : args for name,args in zip(mentioned_tasks, task_args)},
            "non-default-values" : {
                "cmd": non_default_cmd_arg,
                "task" : non_default_task_arg
                }
            }
        return tomlguard.TomlGuard(data)
