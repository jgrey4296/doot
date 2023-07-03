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

PAD : Final[int] = 15

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

@dataclass
class DootParamSpec:
    """ Describes a command line parameter to use in the parser """
    name        : str      = field()
    type        : callable = field(default=bool)

    prefix      : str      = field(default="-")
    default     : Any      = field(default=False)
    desc        : str      = field(default="An undescribed parameter")
    constraints : list     = field(default_factory=list)

    @classmethod
    def from_dict(cls, data:dict) -> DootParamSpec:
        return cls(**data)

    @property
    def short(self):
        return self.name[0]

    @property
    def inverse(self):
        return f"no-{self.name}"

    def _process_value(self, val):
        return val.removeprefix(self.prefix).split("=")

    def __eq__(self, val) -> bool:
        [head, *_] = self._process_value(val)
        return head == self.name or head == self.short or head == self.inverse

    def __str__(self):
        parts = [f"{self.prefix}[{self.name[0]}]{self.name[1:]}"]
        parts.append(" " * (PAD-len(parts[0])))
        match self.type:
            case type() if self.type == bool:
                parts.append(f"{'(bool)': <10}:")
                parts.append(f"Defaults to: {self.default}")
            case str if bool(self.default):
                parts.append(f"{'(str)': <10}:")
                parts.append(f"Defaults to: {self.default}")
            case str:
                parts.append(f"{'(str)': <10}:")


        parts.append(self.desc)
        if self.constraints:
            parts.append("Constrained to: {self.constraints}")
        return " ".join(parts)


    def add_value(self, data, val):
        [head, *rest] = self._process_value(val)
        logging.debug("Matching: %s : %s : %s", self.type.__name__, head, rest)
        match self.type.__name__:
            case "bool" if bool(rest):
                raise TypeError("Bool Arguments shouldn't have values", val)
            case "bool" if head == self.inverse:
                data[self.name] = False
            case "bool":
                data[self.name] = True
            case _ if not bool(rest):
                raise TypeError("non-Bool Arguments should have values", val)
            case "list":
                if self.name not in data:
                    data[self.name] = []
                data[self.name] += rest[0].split(",")
            case "set":
                if self.name not in data:
                    data[self.name] = set()
                data[self.name].update(rest[0].split(","))
            case _ if data.get(self.name, self.default) != self.default:
                raise Exception("Trying to re-set an arg already set", val)
            case _ if len(rest) == 1:
                data[self.name] = self.type(rest[0])
            case _:
                raise Exception("Can't understand raise NotImplementedError()ed in type", val)


class ArgParser_i:
    """
    A Single standard process point for turning the list of passed in args,
    into a dict, into a tomler,
    along the way it determines the cmds and tasks that have been chosne
    """

    def __init__(self):
        self.specs = []

    def add_param_specs(self, specs:list):
        self.specs += specs

    def parse(self, args:list, doot_arg_specs:list, cmds:dict, tasks:dict) -> Tomler:
        raise NotImplementedError()
