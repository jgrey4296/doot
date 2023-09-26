## base_action.py -*- mode: Py -*-
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

printer = logmod.getLogger("doot._printer")

import doot
from doot.errors import DootTaskError, DootTaskFailed
from doot._abstract import Action_p

@doot.check_protocol
class DootBaseAction(Action_p):
    """
    The basic action, which just prints that the action was called
    Subclass this and override __call__ for your own actions.
    The arguments of the action are held in self.spec
    __call__ is passed a *copy* of the task's state dictionary
    """

    def __str__(self):
        return f"Base Action: {self.spec.args}"

    def __call__(self, task_state_copy:dict) -> dict|bool|None:
        printer.debug("Base Action Called: %s", task_state_copy.get("count", 0))
        printer.info(" ".join(self.expand_str(x, task_state_copy) for x in self.spec.args))
        return { "count" : task_state_copy.get("count", 0) + 1 }

    def expand_str(self, val, state):
        return val.format_map(state)
