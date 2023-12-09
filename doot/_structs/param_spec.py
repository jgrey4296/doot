#!/usr/bin/env python3
"""


See EOF for license/metadata/notes as applicable
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
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import importlib
from tomlguard import TomlGuard
import doot.errors
import doot.constants
from doot.enums import TaskFlags, ReportEnum, StructuredNameEnum

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]


@dataclass
class DootParamSpec:
    """ Describes a command line parameter to use in the parser
      When `positional`, will not match against a string starting with `prefix`
      consumed in doot._abstract.parser.ArgParser_i's
      produced using doot._abstract.parser.ParamSpecMaker_m classes,
      like tasks, and taskers
    """
    name        : str      = field()
    type        : type     = field(default=bool)

    prefix      : str      = field(default="-")

    default     : Any      = field(default=False)
    desc        : str      = field(default="An undescribed parameter")
    constraints : list     = field(default_factory=list)
    invisible   : bool     = field(default=False)
    positional  : bool     = field(default=False)
    _short       : None|str = field(default=None)

    _repeatable_types : ClassVar[list[Any]] = [list, int]

    separator   : str      = field(default="=")

    @classmethod
    def from_dict(cls, data:dict) -> DootParamSpec:
        return cls(**data)

    @staticmethod
    def key_func(x):
        return (x.positional, x.prefix)

    @property
    def short(self):
        if self.positional:
            return self.name

        if self._short:
            return self._short

        return self.name[0]

    @property
    def inverse(self):
        return f"no-{self.name}"

    @property
    def repeatable(self):
        return self.type in DootParamSpec._repeatable_types and not self.positional

    def _split_name_from_value(self, val):
        match self.positional:
            case False:
                return val.removeprefix(self.prefix).split(self.separator)
            case True:
                return (self.name, val)

    def __eq__(self, val) -> bool:
        match val, self.positional:
            case DootParamSpec(), _:
                return val is self
            case str(), False:
                [head, *_] = self._split_name_from_value(val)
                return head in [self.name, self.short, self.inverse]
            case str(), True:
                return not val.startswith(self.prefix)
            case _, _:
                return False

    def __str__(self):
        if self.invisible:
            return ""

        if self.positional:
            parts = [self.name]
        else:
            parts = [f"{self.prefix}[{self.name[0]}]{self.name[1:]}"]

        parts.append(" " * (PAD-len(parts[0])))
        match self.type:
            case type() if self.type == bool:
                parts.append(f"{'(bool)': <10}:")
            case str() if bool(self.default):
                parts.append(f"{'(str)': <10}:")
            case str():
                parts.append(f"{'(str)': <10}:")
            case _:
                pass

        parts.append(f"{self.desc:<30}")
        pad = " "*max(0, (85 - (len(parts)+sum(map(len, parts)))))
        match self.default:
            case None:
                pass
            case str():
                parts.append(f'{pad}: Defaults to: "{self.default}"')
            case _:
                parts.append(f"{pad}: Defaults to: {self.default}")

        if self.constraints:
            parts.append(": Constrained to: {self.constraints}")
        return " ".join(parts)

    def __repr__(self):
        if self.positional:
            return f"<ParamSpec: {self.name}>"
        return f"<ParamSpec: {self.prefix}{self.name}>"

    def add_value_to(self, data:dict, val:str) -> bool:
        """ if the given value is suitable, add it into the given data """
        [head, *rest] = self._split_name_from_value(val)
        logging.debug("Matching: %s : %s : %s", self.type.__name__, head, rest)
        match self.type.__name__:
            ##-- handle bools and inversion
            case "bool" if bool(rest):
                raise doot.errors.DootParseError("Bool Arguments shouldn't have values: %s : %s", self.name, val)
            case "bool" if head == self.inverse:
                data[self.name] = False
            case "bool":
                data[self.name] = True
            ##-- end handle bools and inversion
            case _ if not bool(rest):
                raise doot.errors.DootParseError("Non-Bool Arguments should have values: %s : %s", self.name, val)
            case "list":
                if self.name not in data:
                    data[self.name] = []
                data[self.name] += rest[0].split(",")
            case "set":
                if self.name not in data:
                    data[self.name] = set()
                data[self.name].update(rest[0].split(","))
            case _ if data.get(self.name, self.default) != self.default:
                raise doot.errors.DootParseError("Trying to re-set an arg already set: %s : %s", self.name, val)
            case _ if len(rest) == 1:
                data[self.name] = self.type(rest[0])
            case _:
                raise doot.errors.DootParseError("Can't understand value: %s : %s", self.name, val)

        return data[self.name] != self.default



    def maybe_consume(self, args:list[str], data:dict) -> bool:
        """
          Given a list of args, possibly add a value to the data.
          operates in place.
          return True if consumed a value

          handles ["--arg=val"], ["-a", "val"], and, if positional, ["val"]
        """
        if not bool(args) or data is None:
            return False
        if args[0] != self:
            return False

        pop_count = 1
        focus     = args[0]
        prefixed  = focus.startswith(self.prefix)
        is_joint  = self.separator in focus
        key, val  = None, None


        match prefixed, is_joint:
            case True, True: # --key=val
                key, val = focus.split(self.separator)
                key = key.removeprefix(self.prefix)
                pass
            case True, False if self.type.__name__ != "bool" and not bool(args):
                raise doot.errors.DootParseError("key lacks a following value", focus, self.type.__name__)
            case True, False if self.type.__name__ != "bool": # [--key, val]
                key = focus.removeprefix(self.prefix)
                val = args[1]
                pop_count = 2
                pass
            case False, False if self.positional: # [val]
                val = focus
            case _, _: # Nonsense
                key = focus.removeprefix(self.prefix)


        match self.type.__name__:
            ## handle bools and inversion
            case "bool" if val is not None:
                raise doot.errors.DootParseError("Bool Arguments shouldn't have values: %s : %s", self.name, val)
            case "bool" if key == self.inverse:
                data[self.name] = False
            case "bool":
                data[self.name] = True
            case _ if val is None:
                raise doot.errors.DootParseError("Non-Bool Arguments should have values: %s : %s", self.name, val)
            ## lists
            case "list" if not isinstance(data[self.name], list):
                raise doot.errors.DootParseError("List param doesn't have a list entry in data dict", self.name)
            case "list":
                data[self.name] += val.split(",")
            case "set" if not isinstance(data[self.name], set):
                raise doot.errors.DootParseError("Set param doesn't have a set entry in data dict", self.name)
            case "set":
                data[self.name].update(val.split(","))
            case _ if data.get(self.name, self.default) != self.default:
                raise doot.errors.DootParseResetError("Trying to re-set an arg already set: %s : %s", self.name, val)
            case _:
                data[self.name] = self.type(val)


        for x in range(pop_count):
            args.pop(0)

        return True




"""


"""
