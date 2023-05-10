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

import tomler
import doot
from doot._abstract.parser import DootParser_i


class DootArgParser(DootParser_i):
    """
    convert argv to tomler by:
    parsing each arg as toml,
    """

    def __init__(self):
        pass

    def setup_args(self):
        return [
            {"name": "target", "short": "t", "type": maybe_build_path, "default": None},
            {"name": "all", "long": "all", "type": bool, "default": self.glob_all_as_default},
            {"name": "some", "long": "some", "type": float, "default": -1.0 },
            {"name" : "list", "long": "list", "short": "l", "type": bool, "default": False},
        ]

    def parse(self, args:list):
        logging.debug("Parsing args: %s", args)
        data = {}

        for arg in args[1:]:



        return tomler.Tomler(table=data)
