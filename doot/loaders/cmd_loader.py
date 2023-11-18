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

import tomler
import time
import doot
from doot._abstract import CommandLoader_p, Command_i

@doot.check_protocol
class DootCommandLoader(CommandLoader_p):
    """
      Default Command loaded. using the loaded plugins,
      selects "command", calls load on each entry point, and if the obj returned is a subclass of Command_i,
      instantiates it
    """

    def setup(self, plugins, extra=None) -> Self:
        self.cmd_plugins : list[EntryPoint] = plugins.get("command", [])
        self.cmds = {}

        match extra:
            case None:
                self.extra = []
            case list():
                self.extra = extra
            case dict():
                self.extra = tomler.Tomler(extra).on_fail([]).tasks()
            case tomler.Tomler():
                self.extra = tomler.on_fail([]).tasks()

        return self

    def load(self) -> Tomler[Command_i]:
        logging.debug("---- Loading Commands")
        for cmd_point in self.cmd_plugins:
            try:
                logging.debug("Loading Cmd: %s", cmd_point.name)
                # load the plugins
                cmd = cmd_point.load()
                if not issubclass(cmd, Command_i):
                    raise TypeError("Not a Command_i", cmd)

                self.cmds[cmd_point.name] = cmd()
                self.cmds[cmd_point.name]._name = cmd_point.name
            except Exception as err:
                raise doot.errors.DootPluginError("Attempted to load a non-command: %s : %s", cmd_point, err) from err

        return tomler.Tomler(self.cmds)
