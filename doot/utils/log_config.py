#!/usr/bin/env python3
"""

"""

##-- builtin imports
from __future__ import annotations

# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1

##-- end builtin imports

##-- boltons
# import boltons.cacheutils
# import boltons.debugutils
# import boltons.deprutils
# import boltons.dictutils
# import boltons.easterutils
# import boltons.ecoutils
# import boltons.excutils
# import boltons.fileutils
# import boltons.formatutils
# import boltons.funcutils
# import boltons.gcutils
# import boltons.ioutils
# import boltons.iterutils
# import boltons.jsonutils
# import boltons.listutils
# import boltons.mathutils
# import boltons.mboxutils
# import boltons.namedutils
# import boltons.pathutils
# import boltons.queueutils
# import boltons.setutils
# import boltons.socketutils
# import boltons.statsutils
# import boltons.strutils
# import boltons.tableutils
# import boltons.tbutils
# import boltons.timeutils
# import boltons.typeutils
# import boltons.urlutils
##-- end boltons

##-- lib imports
# from bs4 import BeautifulSoup
# import construct as C
# import dirty-equals as deq
# import graphviz
# import matplotlib.pyplot as plt
import more_itertools as mitz
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
# import spacy # nlp = spacy.load("en_core_web_sm")
# import stackprinter # stackprinter.set_excepthook(style='darkbg2')
# import sty
# import sympy
# import tomllib
# import toolz
# import tqdm
# import validators
# import z3
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from sys import stdout, stderr
import doot
import doot.constants

class _DootAnyFilter:

    def __init__(self, names=None, reject=None):
        self.names      = names or []
        self.rejections = reject or []
        self.name_re    = re.compile("^({})".format("|".join(self.names)))

    def __call__(self, record):
        return (record.name not in self.rejections) and (record.name == "root"
                                                         or not bool(self.names)
                                                    or self.name_re.match(record.name))

class DootLogConfig:
    """ Utility class to setup [stdout, stderr, file] logging. """

    def __init__(self):
        # Root Logger for everything
        self.root    = logmod.root
        # EXCEPT this, which replaces 'print(x)'
        self.printer = logmod.getLogger(doot.constants.PRINTER_NAME)

        self.file_handler   = logmod.FileHandler(pl.Path() / "log.doot", mode='w')
        self.stream_handler = logmod.StreamHandler(stdout)
        self.print_stream_handler  = logmod.StreamHandler(stdout)

        self._setup()

    def _setup(self):
        """ a basic, config-less setup """
        self.root.setLevel(logmod.NOTSET)
        self.file_handler.setFormatter(logmod.Formatter("{levelname} : INIT : {message}", style="{"))

        self.stream_handler.setLevel(logmod.WARNING)
        self.stream_handler.setFormatter(logmod.Formatter("{levelname}  : INIT : {message}", style="{"))

        self.root.addHandler(self.file_handler)
        self.root.addHandler(self.stream_handler)

        self.printer.propagate = False
        self.print_stream_handler.setFormatter(logmod.Formatter("{message}", style="{"))
        self.printer.setLevel(logmod.NOTSET)
        self.printer.addHandler(self.print_stream_handler)
        self.printer.addHandler(self.file_handler)

    def setup(self):
        """ a setup that uses config values """
        file_log_level    = doot.config.on_fail("DEBUG", str|int).logging.file.level(wrapper=lambda x: logmod._nameToLevel.get(x, 0))
        file_log_format   = doot.config.on_fail("{levelname} : {pathname} : {lineno} : {funcName} : {message}", str).logging.file.format()
        file_filter_names = doot.config.on_fail([], list).logging.file.filters()

        self.file_handler.setLevel(file_log_level)
        self.file_handler.setFormatter(logmod.Formatter(file_log_format, style="{"))
        if bool(file_filter_names):
            self.file_handler.addFilter(_DootAnyFilter(file_filter_names))

        stream_log_level    = doot.config.on_fail("WARNING", str|int).logging.stream.level(wrapper=lambda x: logmod._nameToLevel.get(x, 0))
        stream_log_format   = doot.config.on_fail("{levelname} : {pathname} : {lineno} : {funcName} : {message}", str).logging.stream.format()
        stream_filter_names = doot.config.on_fail([], list).logging.stream.filters()

        self.stream_handler.setLevel(stream_log_level)
        self.stream_handler.setFormatter(logmod.Formatter(stream_log_format, style="{"))
        if bool(stream_filter_names):
            self.stream_handler.addFilter(_DootAnyFilter(stream_filter_names))

    def set_level(self, level):
        self.stream_handler.setLevel(level)
