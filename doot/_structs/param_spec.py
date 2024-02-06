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
from doot.enums import TaskFlags, ReportEnum

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]

@dataclass
class DootParamSpec:
    """ Describes a command line parameter to use in the parser
      When `positional`, will not match against a string starting with `prefix`
      consumed in doot._abstract.parser.ArgParser_i's
      produced using doot._abstract.parser.ParamSpecMaker_m classes,
      like tasks, and jobs
    """
    name        : str                       = field()
    type        : type                      = field(default=bool)

    prefix      : str                       = field(default="-")

    default     : Any                       = field(default=False)
    desc        : str                       = field(default="An undescribed parameter")
    constraints : list                      = field(default_factory=list)
    invisible   : bool                      = field(default=False)
    positional  : bool|int                  = field(default=False)
    _short       : None|str                 = field(default=None)

    _repeatable_types : ClassVar[list[Any]] = [list, int]

    separator   : str                       = field(default="=")

    @classmethod
    def from_dict(cls, data:TomlGuard|dict) -> DootParamSpec:
        param =  cls(**data)
        match param:
            case DootParamSpec(type="int"):
                param.type = int
            case DootParamSpec(type="float"):
                param.type = float
            case DootParamSpec(type="bool"):
                param.type = bool
            case DootParamSpec(type="str"):
                param.type = str
            case DootParamSpec(type="list"):
                param.type = list

        if param.default == "None":
            param.default = None

        return param

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
            case True if isinstance(val, list):
                return (self.name, val)
            case True | int():
                return (self.name, [val])

    def __eq__(self, val) -> bool:
        match val, self.positional:
            case DootParamSpec(), _:
                return val is self
            case str(), False:
                [head, *_] = self._split_name_from_value(val)
                return head in [self.name, self.short, self.inverse]
            case str(), True:
                return not val.startswith(self.prefix)
            case str(), int():
                return not val.startswith(self.prefix)
            case _, _:
                return False

    def __str__(self):
        if self.invisible:
            return ""

        parts = [self.key_str or f"[{self.name}]"]

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

    @property
    def key_str(self):
        if self.invisible or self.positional:
            return ""

        if self.prefix == doot.constants.PARAM_ASSIGN_PREFIX:
            return f"{self.prefix}{self.name}{self.separator}"

        return f"{self.prefix}{self.name}"

    @property
    def short_key_str(self):
        if self.invisible or self.positional:
            return ""

        if self.prefix == doot.constants.PARAM_ASSIGN_PREFIX:
            return f"{self.prefix}{self.name[0]}{self.separator}"

        return f"{self.prefix}{self.name[0]}"

    def maybe_consume(self, args:list[str], data:dict) -> bool:
        """
          Given a list of args, possibly add a value to the data.
          operates *in place* on both the args list and the data.
          return True if consumed a value

          handles:
          ["--arg=val"],
          ["-arg", "val"],
          ["val"],     (if positional=True)
          ["-arg"],    (if type=bool)
          ["-no-arg"], (if type=bool)
        """
        if not bool(args) or data is None or args[0] != self:
            return False

        pop_count  = 1
        focus      = args[0]
        prefixed   = focus.startswith(self.prefix)
        is_assign  = self.separator in focus
        key, vals  = None, []

        # Figure out the key and value
        match prefixed, is_assign:
            case _, True if self.prefix != doot.constants.PARAM_ASSIGN_PREFIX:
                raise doot.errors.DootParseError("Assignment parameters should be prefixed with the PARAM_ASSIGN_PREFIX", doot.constants.PARAM_ASSIGN_PREFIX)
            case True, True: # --key=val
                key, val = focus.split(self.separator)
                key = key.removeprefix(self.prefix)
                vals.append(val)
            case True, False if self.type.__name__ != "bool" and not bool(args):
                raise doot.errors.DootParseError("key lacks a following value", focus, self.type.__name__)
            case True, False if self.type.__name__ == "bool": # --key
                key = focus.removeprefix(self.prefix)
            case True, False: # -key val
                key = focus.removeprefix(self.prefix)
                vals.append(args[1])
                pop_count = 2
            case False, False if self.positional and data.get(self.name, self.default) == self.default:
                key = self.name
                vals.append(focus)
            case False, False if self.positional and self.type == list:
                key = self.name
                vals.append(focus)
            case False, False if not isinstance(self.positional, bool) and len(data.get(self.name, [])) < self.positional:
                key = self.name
                vals.append(focus)
            case _, _: # Nonsense
                pass

        if key is None or vals is None:
            return False

        # correct form, and the key is self, so add it to data
        if self.positional:
            self._add_positional_value(data, key=key, vals=vals)
        else:
            self._add_non_positional_value(data, key=key, vals=vals)

        # data has been added, so remove it from the input list
        for x in range(pop_count):
            args.pop(0)

        return True

    def _add_non_positional_value(self, data:dict, *, key:str=None, vals:list[str]=None) -> bool:
        """ if the given value is suitable, add it into the given data
        takes separated key, values,
        and the key has had the prefix stripped
        """
        vals = vals or []
        # TODO if constraints, check against them
        logging.debug("Matching: %s : %s : %s", self.type.__name__, key, vals)

        # Use type.__name__ because you can't match on type. ("case str" fails, expecting "case str()")
        match self.type.__name__:
            case "list":
                if self.name not in data or data[self.name] == self.default:
                    data[self.name] = []
                data[self.name] += vals
            case "set":
                if self.name not in data or data[self.name] == self.default:
                    data[self.name] = set()
                data[self.name].update(vals)
            case _ if data.get(self.name, self.default) != self.default:
                raise doot.errors.DootParseError("Trying to re-set an arg already set: %s : %s", self.name, vals)
            ##-- handle bools and inversion
            case "bool" if bool(vals):
                raise doot.errors.DootParseError("Bool Arguments shouldn't have values: %s : %s", self.name, vals)
            case "bool" if key == self.inverse:
                data[self.name] = False
            case "bool":
                data[self.name] = True
            ##-- end handle bools and inversion
            case _ if not bool(vals):
                raise doot.errors.DootParseError("Non-Bool Arguments should have values: %s : %s", self.name, vals)
            case _ if len(vals) == 1:
                data[self.name] = self.type(vals[0])
            case _:
                raise doot.errors.DootParseError("Can't understand value: %s : %s", self.name, vals)

        return data[self.name] != self.default

    def _add_positional_value(self, data, *, key:str=None, vals:list[str]=None):
        # TODO if constraints, check against them
        match self.positional:
            case True:
                data[self.name] = self.type(vals[0])
            case int() if self.type.__name__ != "list":
                raise doot.errors.DootParseError("Multi-positional args should be of type 'list'", self.name)
            case int():
                if data[self.name] == self.default:
                    data[self.name] = []
                data[self.name] += vals

        if not isinstance(self.positional, bool) and self.positional < len(data[self.name]):
            raise doot.errors.DootParseError("Too many positional args provided", self.name)
