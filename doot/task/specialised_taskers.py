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

from doot.task.base_tasker import DootTasker

class DictTasker(DootTasker):
    """ Make a tasker from just a dict """
    pass

class FunctionTasker(DootTasker):
    """ Make a tasker from just a function """
    pass

class GroupTasker(DootTasker):
    """ A Group of task specs, none of which require params """

    def __init__(self, name, *args, as_creator=False):
        self.name       = name.replace(" ", "_")
        self.tasks      = list(args)
        self.as_creator = as_creator

    def __str__(self):
        return f"group:{self.name}({len(self)})"

    def __len__(self):
        return len(self.tasks)

    def __iadd__(self, other):
        self.tasks.append(other)
        return self

    def to_dict(self):
        # this can add taskers to the namespace,
        # but doesn't help for dicts
        return {f"doot_{self.name}_{id(x)}": x for x in self.tasks}

    def add_tasks(self, *other):
        for x in other:
            self.tasks.append(other)

class WatchTasker(DootTasker):
    """
    Tasker that watches for conditions, *then*
    generates tasks.
    eg: a file watcher
    """
    pass
