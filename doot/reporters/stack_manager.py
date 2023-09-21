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
                    cast, final, overload, runtime_checkable, Generator)
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

from doot._abstract import Reporter_i, ReportLine_i
from doot.structs import DootTraceRecord

class DootReportManagerStack(Reporter_i):
    """
    A Stack of Reporters to try using.
    The First one that returns a DootTrace is used.
    """

    def __init__(self, reporters:list[ReportLine_i]=None):
        super().__init__(reporters)

    def __str__(self):
        result = []
        for trace in self._full_trace:
            for reporter in self._reporters:
                match reporter(trace):
                    case None:
                        continue
                    case str() as res:
                        result.append(res)

        return "\n".join(result)
