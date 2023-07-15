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
printer = logmod.getLogger("doot._printer")

import doot
from doot._abstract.cmd import Command_i
from collections import defaultdict


class HelpCmd(Command_i):
    _name      = "help"
    _help      = ["Print info about the specified cmd or task"]

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            # self.make_param(name="target", type=str, default=""),
            self.make_param(name="target", type=str, positional=True, default="")
            ]

    def __call__(self, tasks, plugins):
        """List task generators"""
        if doot.args.cmd.args.help:
            printer.info(self.help)
            return

        if doot.args.cmd.args.target == "" and not bool(doot.args.tasks):
            # Print general help and list cmds
            printer.info("No Target Specified")
            printer.info("Available Command Targets: ")
            for x in sorted(plugins.command, key=lambda x: x.name):
                printer.info("-- %s", x.name)
            return

        task_targets = [tasks[x] for x in doot.args.tasks.keys()]
        cmd_targets  = []

        if doot.args.cmd.args.target:
            # Print help of just the specified target
            cmd_targets += [x for x in plugins.command if x.name == doot.args.cmd.args.target]
            task_targets += [y for x,y in tasks.items() if doot.args.cmd.args.target in x ]

        logging.debug("Matched %s commands", len(cmd_targets))
        if len(cmd_targets) == 1:
            printer.info(cmd_targets[0].load()().help)


        for i, spec in enumerate(task_targets):
            self.print_task_spec(i, spec)

        printer.info("\n------------------------------")
        printer.info("DOOT HELP END: %s Tasks Matched", len(task_targets))


    def print_task_spec(self, count, spec):
        spec_dict, tasker_cls = spec
        lines = []
        lines.append("")
        lines.append("------------------------------")
        lines.append(f"{count:4}: Task: {spec_dict['name']}")
        lines.append("------------------------------")
        lines.append(f"ver    : {spec_dict.get('ver','0.1')}")
        lines.append(f"Group  : {spec_dict['group']}")
        lines.append(f"Source : {spec_dict['source']}")

        lines.append(tasker_cls.help)
        match spec_dict.get('doc', None):
            case None:
                pass
            case str():
                lines.append("")
                lines.append(f"--   {spec_dict['doc']}")
            case list() as xs:
                lines.append("")
                lines.append("--  " + "\n--  ".join(xs))

        printer.info("\n".join(lines))
