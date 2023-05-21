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

class DootCommandLoader(CommandLoader_i):

    def setup(self, plugins):
        self.cmd_plugins : list[EntryPoint] = plugins.get("command", [])

    def load(self, args:Tomler) -> dict[str, DootCommand_i]:
        logging.debug("Loading Commands")
        cmds = {}
        for cmd_point in self.cmd_plugins:
            try:
                # load the plugins
                cmd = cmd_point.load()
                if not isinstance(cmd, DootCommand_i):
                    raise Exception()

                cmds[cmd._name] = cmd()
            except Exeption as err:
                raise ResourceWarning(f"Attempted to load a non-command: {cmd_point}") from err


        return []
