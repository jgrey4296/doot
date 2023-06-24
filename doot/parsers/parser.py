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

# from bs4 import BeautifulSoup
# import boltons
# import construct as C
# import dirty-equals as deq
# import graphviz
# import matplotlib.pyplot as plt
# import more_itertools as itzplus
# import networkx as nx
# import numpy as np
# import pandas
# import pomegranate as pom
# import pony import orm
# import pronouncing
# import pyparsing as pp
# import rich
# import seaborn as sns
# import sklearn
# import stackprinter # stackprinter.set_excepthook(style='darkbg2')
# import sty
# import sympy
# import tomllib
# import toolz
# import tqdm
# import validators
# import z3
# import spacy # nlp = spacy.load("en_core_web_sm")

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import tomler
import doot
from doot._abstract.parser import ArgParser_i, DootParamSpec
from collections import ChainMap

class DootArgParser(ArgParser_i):
    """
    convert argv to tomler by:
    parsing each arg as toml,

    # doot {args} {cmd} {cmd_args}
    # doot {args} [{task} {task_args}] - implicit do cmd
    """


    def parse(self, args:list, doot_specs:list[DootParamSpec], cmds:Tomler, tasks:Tomler) -> Tomler:
        logging.debug("Parsing args: %s", args)
        head_arg     = args[0]
        doot_args    = { x.name : x.default for x in doot_specs }

        cmd          = None
        cmd_name     = None
        cmd_args     = {}

        chosen_tasks = []
        task_names   = []
        task_args    = []

        named_cmds    = list(cmds.keys())
        named_tasks   = list(tasks.keys())
        current_specs = doot_specs
        focus         = "doot"

        logging.debug("Registered Arg Specs: %s", current_specs)
        for arg in args[1:]:
            matching_specs = [x for x in current_specs if x == arg]
            if len(matching_specs) > 1:
                logging.warning("Multiple matching arg specs, use it's full name: %s : %s", arg, [x.name for x in matching_specs])
                raise Exception()

            match focus:
                case "doot" if arg in named_cmds:
                    focus         = "cmd"
                    cmd           = cmds[arg]
                    current_specs = cmd.param_specs
                    cmd_name      = arg
                    cmd_args      = { x.name : x.default for x in current_specs }
                case "doot" | "cmd" | "task" if arg in task_names:
                    raise Exception("Duplicated task")
                case "doot" | "cmd" | "task" if arg in named_tasks:
                    focus         = "task"
                    chosen_tasks.append(tasks[arg])
                    task_names.append(arg)
                    current_specs = chosen_tasks[-1].param_specs
                    new_task_args = { x.name : x.default for x in current_specs }
                    task_args.append(new_task_args)
                case "doot" if bool(matching_specs):
                    spec = matching_specs[0]
                    spec.add_value(doot_args, arg)
                case "cmd" if bool(matching_specs):
                    spec = matching_specs[0]
                    spec.add_value(cmd_args, arg)
                case "task" if bool(matching_specs):
                    spec = matching_specs[0]
                    spec.add_value(task_args[-1], arg)
                case _ if not (bool(doot_specs) or bool(cmds) or bool(tasks)):
                    pass
                case _:
                    raise Exception("Unrecognized Arg", arg)

        data = {
            "head" : {"name": head_arg,
                      "args": doot_args },
            "cmd" : {"name" : cmd_name or doot.constants.default_cli_cmd,
                     "args" : cmd_args },
            "tasks" : {name : args for name,args in zip(task_names, task_args)}

            }
        return tomler.Tomler(data)
