#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from abc import abstractmethod
from tomlguard import TomlGuard
from doot.structs import DootParamSpec


@dataclass
class _RegexEqual(str):
    """ https://martinheinz.dev/blog/78 """
    string : str
    match :  re.Match = None

    def __eq__(self, pattern):
        self.match = re.search(pattern, self.string)
        return self.match is not None

    def __getitem__(self, group):
        return self.match[group]

class ParamSpecMaker_m:

    @staticmethod
    def make_param(*args:Any, **kwargs:Any) -> DootParamSpec:
        """ Utility method for easily making paramspecs """
        return DootParamSpec(*args, **kwargs)

class ArgParser_i:
    """
    A Single standard process point for turning the list of passed in args,
    into a dict, into a tomlguard,
    along the way it determines the cmds and tasks that have been chosne
    """

    def __init__(self):
        self.specs = []

    def add_param_specs(self, specs:list):
        self.specs += specs

    @abstractmethod
    def parse(self, args:list[str], doot_arg_specs:list[DootParamSpec], cmds:TomlGuard, tasks:TomlGuard) -> TomlGuard:
        raise NotImplementedError()
