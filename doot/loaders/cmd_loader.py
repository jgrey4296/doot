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
import importlib
from importlib.metadata import entry_points
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
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

import time
import doot
from doot._abstract.loader import CommandLoader_i
from doot._abstract.cmd import DootCommand_i

##-- loader cli params
#### options related to dooter.py
# select dodo file containing tasks
opt_doot = {
    "section" : "task loader",
    "name"    : "dooter",
    "short"   : "f",
    "long"    : "file",
    "type"    : str,
    "default" : str(doot.default_dooter),
    "env_var" : "DOOT_FILE",
    "help"    : "load task from doot FILE [default: %(default)s]"
}

opt_break = {
    "section" : "task loader",
    "name"    : "break",
    "short"   : "b",
    "long"    : "break",
    "type"    : bool,
    "default" : False,
    "help"    : "Start a debugger before loading tasks, to set breakpoints"
    }

# cwd
opt_cwd = {
    'section': 'task loader',
    'name': 'cwdPath',
    'short': 'd',
    'long': 'dir',
    'type': str,
    'default': None,
    'help': ("set path to be used as cwd directory "
             "(file paths on dodo file are relative to dodo.py location).")
}

# seek dodo file on parent folders
opt_seek_file = {
    'section': 'task loader',
    'name': 'seek_file',
    'short': 'k',
    'long': 'seek-file',
    'type': bool,
    'default': False,
    'env_var': 'DOIT_SEEK_FILE',
    'help': ("seek dodo file on parent folders [default: %(default)s]")
}

##-- end loader cli params

class DootCommandLoader(CommandLoader_i):

    def setup(self, plugins):
        # get cmd plugins from plugins
        self.cmd_plugins : list[EntryPoint] = plugins.get("command", [])
        # add doot.constants.default_cmds

    def load(self, args:Tomler) -> dict[str, DootCommand_i]:
        logging.debug("Loading Commands")
        # load the plugins
        return []
