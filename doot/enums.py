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

class TaskStateEnum(enum.Enum):
    """
      Enumeration of the different states a task can be in.
      The state is stored in a TaskTracker_i
    """
    TEARDOWN        = enum.auto()
    SUCCESS         = enum.auto()
    FAILED          = enum.auto()
    HALTED          = enum.auto()
    WAIT            = enum.auto()
    READY           = enum.auto()
    EXISTS          = enum.auto()
    INIT            = enum.auto()
    DEFINED         = enum.auto()
    DECLARED        = enum.auto()
    ARTIFACT        = enum.auto()

class TaskFlags(enum.Flag):
    """
      Flags describing properties of a task,
      stored in the Task_i instance itself.
    """
    TASK         = enum.auto()
    TASKER       = enum.auto()
    EPHEMERAL    = enum.auto()
    IDEMPOTENT   = enum.auto()
    REQ_TEARDOWN = enum.auto()
    REQ_SETUP    = enum.auto()
    IS_TEARDOWN  = enum.auto()
    IS_SETUP     = enum.auto()
    THREAD_SAFE  = enum.auto()
    STATEFUL     = enum.auto()
    STATELESS    = enum.auto()

class ReportPositionEnum(enum.Flag):
    INIT     = enum.auto()
    SUCCEED  = enum.auto()
    FAIL     = enum.auto()
    EXECUTE  = enum.auto()
    SKIP     = enum.auto()

    STALE    = enum.auto()
    CLEANUP  = enum.auto()

    STATUS   = enum.auto()

    PLUGIN   = enum.auto()
    TASK     = enum.auto()
    TASKER   = enum.auto()
    ACTION   = enum.auto()
    CONFIG   = enum.auto()

class StructuredNameEnum(enum.Enum):
    TASK  = enum.auto()
    CLASS = enum.auto()
