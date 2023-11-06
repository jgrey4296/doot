## base_action.py -*- mode: python -*-
##-- imports
from __future__ import annotations

# import abc
import datetime
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

from time import sleep
import sh
import shutil
import doot
from doot.errors import DootTaskError, DootTaskFailed
from doot._abstract import Action_p

@doot.check_protocol
class WriteAction(Action_p):
    """
      Writes data from the task_state_copy to a file, accessed throug the
      doot.locs object
    The arguments of the action are held in self.spec
    __call__ is passed a *copy* of the task's state dictionary

    """

    def __str__(self):
        return f"Base Action: {self.spec.args}"

    def expand_str(self, val, state):
        return val.format_map(state)

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        fname = spec.kwargs.on_fail((None,)).fname()
        if fname is not None:
            fname = self.expand_str(fname, task_state)

        target_key = spec.kwargs.target
        data_key   = spec.kwargs.data
        if target_key in task_state:
            target = task_state.get(target_key)
        else:
            target = target_key

        if data_key in task_state:
            data = task_state.get(data_key)
        else:
            data = data_key


        loc = doot.locs[target]
        if fname is not None:
            loc = loc / fname
        printer.info("Writing to %s", loc)
        with open(loc, 'w') as f:
            f.write(data)


@doot.check_protocol
class ReadAction(Action_p):
    """
      Reads data from the doot.locs location to  return for the task_state
      The arguments of the action are held in self.spec
      __call__ is passed a *copy* of the task's state dictionary

    """

    def __str__(self):
        return f"Base Action: {self.spec.args}"

    def __call__(self, spec, task_state_copy:dict) -> dict|bool|None:
        target_key = spec.kwargs.target
        data_key   = spec.kwargs.data
        if target_key in task_state:
            target = task_state.get(target_key)
        else:
            target = target_key

        loc = doot.locs[target]
        printer.info("Reading from %s into %s", loc, data_key)
        with open(loc, 'r') as f:
            match spec.kwargs.on_fail("read").type():
                case "read":
                    return { data_key : f.read() }
                case "lines":
                    return { data_key : f.readlines() }
                case unk:
                    raise TypeError("Unknown read type", unk)


@doot.check_protocol
class CopyAction(Action_p):
    """
      copy a file somewhere
      The arguments of the action are held in self.spec
      __call__ is passed a *copy* of the task's state dictionary

    """

    def __str__(self):
        return f"Base Action: {self.spec.args}"

    def __call__(self, spec, task_state_copy:dict) -> dict|bool|None:
        target_key = spec.kwargs.target
        source_key = spec.kwargs.source

        if target_key in task_state:
            target = task_state.get(target_key)
        else:
            target = target_key

        if source_key in task_state:
            source = task_state.get(source_key)
        else:
            source = source_key

        source_loc = doot.locs[source]
        target_loc = doot.locs[target]
        printer.info("Copying from %s to %s", source_loc, target_loc)
        shutil.copy2(source_loc,target_loc)
