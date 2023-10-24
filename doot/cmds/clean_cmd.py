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
from doot._abstract import Command_i
from collections import defaultdict


class CleanCmd(Command_i):
    """
      Runs either a general clean command, or a specific task clean command
    """
    _name      = "clean"
    _help      = []

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            self.make_param(name="target", type=str, default=""),
            self.make_param(name="recursive", type=bool, default=False)
            ]

    def __call__(self, tasks:dict, plugins:dict):
        if bool(doot.args.on_fail(None).cmd.args.target()):
            printer.info("TODO: Clean targeting %s", doot.args.on_fail.cmd.args.target)
        else:
            printer.info("TODO: General Clean")
