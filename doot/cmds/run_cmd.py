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

import doot
from doot._abstract.cmd import Command_i
from collections import defaultdict

printer = logmod.getLogger("doot._printer")

class RunCmd(Command_i):
    _name      = "run"
    _help      = []

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            self.make_param(name="target", type=str, default=""),
            self.make_param(name="step", default=False),
            self.make_param(name="dry-run", default=False),
            self.make_param
            ]

    def __call__(self, tasks:Tomler, plugins:Tomler):
        raise NotImplementedError("Run Command")
        tracker = plugins.tracker[0].load()()
        for task in tasks.values():
            tracker.add_task(task)

        target = doot.args.on_fail((None,)).cmd.args.target()
        if target in tracker:
            printer.info("Running Tasks: %s", target)
            reporter = plugins.reporter[0].load()()
            runner = plugins.runner(tracker, reporter)
            # TODO get the tasker, expand it, do it
            return runner(doot.args.cmd.target)

        printer.info("No Run Target Specified")
