#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
# import abc
import datetime
import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from types import GenericAlias
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import more_itertools as mitz
from pydantic import (BaseModel, Field, InstanceOf,
                      field_validator, model_validator)
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import ParamStruct_p, ProtocolModelMeta, Buildable_p
from doot.enums import Report_f, TaskMeta_f

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class ParamSpec(BaseModel, ParamStruct_p, Buildable_p, metaclass=ProtocolModelMeta, arbitrary_types_allowed=True):
    """ Describes a command line parameter to use in the parser
      When `positional`, will not match against a string starting with `prefix`
      consumed in doot._abstract.parser.ArgParser_i's
      produced using doot._abstract.parser.ParamSpecMaker_m classes,
      like tasks, and jobs
    """

    name               : str
    type_              : InstanceOf[type]|Callable = Field(default=bool, alias="type")

    default            : Any                       = False
    desc               : str                       = "An undescribed parameter"
    constraints        : list                      = []
    invisible          : bool                      = False
    positional         : bool|int                  = False
    prefix             : str                       = "-"
    separator          : str                       = "="

    _short             : None|str                  = None
    _consumed          : int                       = 0
    _repeatable_types  : ClassVar[list[Any]]       = [list, int]
    _pad               : ClassVar[int]             = 15

    @classmethod
    def build(cls:BaseModel, data:TomlGuard|dict) -> ParamSpec:
        param =  cls.model_validate(data)
        return param

    @staticmethod
    def key_func(x):
        return (x.positional != 0, x.prefix)

    @field_validator("type_", mode="before")
    def validate_type(cls, val):
        match val:
            case "int":
                return int
            case "float":
                return float
            case "bool":
                return bool
            case "str":
                return str
            case "list":
                return list
            case type():
                return val
            case _:
                return Any

    @field_validator("default")
    def validate_default(cls, val):
        match val:
            case "None":
                return None
            case _:
                 return val

    @ftz.cached_property
    def short(self):
        if self.positional:
            return self.name

        if self._short:
            return self._short

        return self.name[0]

    @ftz.cached_property
    def inverse(self):
        return f"no-{self.name}"

    @ftz.cached_property
    def repeatable(self):
        return self.type_ in ParamSpec._repeatable_types and not self.positional

    @ftz.cached_property
    def key_str(self):
        if self.invisible or self.positional:
            return ""

        if self.prefix == doot.constants.patterns.PARAM_ASSIGN_PREFIX:
            return f"{self.prefix}{self.name}{self.separator}"

        return f"{self.prefix}{self.name}"

    @ftz.cached_property
    def short_key_str(self):
        if self.invisible or self.positional:
            return ""

        if self.prefix == doot.constants.patterns.PARAM_ASSIGN_PREFIX:
            return f"{self.prefix}{self.name[0]}{self.separator}"

        return f"{self.prefix}{self.name[0]}"

    def _split_name_from_value(self, val):
        match self.positional:
            case False:
                return val.removeprefix(self.prefix).split(self.separator)
            case True if isinstance(val, list):
                return (self.name, val)
            case True | int():
                return (self.name, [val])

    def __eq__(self, val) -> bool:
        """ test to see if a cli argument matches this param """
        if 0 < self.positional <= self._consumed:
            return False

        match val, self.positional:
            case ParamSpec(), _:
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

        parts.append(" " * (self._pad - len(parts[0])))
        match self.type_:
            case type() if self.type_ == bool:
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

    def _calc_positional_consumption(self, focus, args):
        pop_count     = 1
        prefixed      = focus.startswith(self.prefix) # form of -param
        is_assign     = self.separator in focus       # form of --param=arg
        key, vals     = None, []

        # Figure out the key and value
        match prefixed, is_assign:
            case _, True if self.prefix != doot.constants.patterns.PARAM_ASSIGN_PREFIX:
                raise doot.errors.DootParseError(
                    "Assignment parameters should be prefixed with the PARAM_ASSIGN_PREFIX",
                    doot.constants.patterns.PARAM_ASSIGN_PREFIX,
                )
            case True, False if self.type_.__name__ != "bool" and not bool(args):
                raise doot.errors.DootParseError(
                    "key lacks a following value", focus, self.type_.__name__
                )
            case True, True: # --key=val
                key, val = focus.split(self.separator)
                key = key.removeprefix(self.prefix)
                vals.append(val)
            case True, False if self.type_.__name__ == "bool": # --key
                key = focus.removeprefix(self.prefix)
            case True, False: # -key val
                key = focus.removeprefix(self.prefix)
                vals.append(args[1])
                pop_count = 2

        return key, vals, pop_count

    def _add_non_positional_value(self, data:dict, *, key:str=None, vals:list[str]=None) -> bool:
        """ if the given value is suitable, add it into the given data
        takes separated key, values,
        and the key has had the prefix stripped
        """
        vals = vals or []
        # TODO if constraints, check against them
        logging.debug("Matching: %s : %s : %s", self.type_.__name__, key, vals)

        # Use type.__name__ because you can't match on type. ("case str" fails, expecting "case str()")
        match self.type_.__name__:
            case "list":
                if self.name not in data or data[self.name] == self.default:
                    data[self.name] = []
                data[self.name] += vals
            case "set":
                if self.name not in data or data[self.name] == self.default:
                    data[self.name] = set()
                data[self.name].update(vals)
            case "Any":
                data[self.name] = vals[0]
            case _ if data.get(self.name, self.default) != self.default:
                raise doot.errors.DootParseError(
                    "Trying to re-set an arg already set: %s : %s", self.name, vals
                )
            ##-- handle bools and inversion
            case "bool" if bool(vals):
                raise doot.errors.DootParseError(
                    "Bool Arguments shouldn't have values: %s : %s", self.name, vals
                )
            case "bool" if key == self.inverse:
                data[self.name] = False
            case "bool":
                data[self.name] = True
            ##-- end handle bools and inversion
            case _ if not bool(vals):
                raise doot.errors.DootParseError(
                    "Non-Bool Arguments should have values: %s : %s", self.name, vals
                )
            case _ if len(vals) == 1:
                data[self.name] = self.type_(vals[0])
            case _:
                raise doot.errors.DootParseError("Can't understand value: %s : %s", self.name, vals)

        return data[self.name] != self.default

    def _add_positional_value(self, data, *, key:str=None, vals:list[str]=None) -> int:
        pop_count = 1
        end_index = None if "--" not in vals else vals.index("--")

        match self.positional:
            case True if self.type_ != list:
                data[self.name] = vals[0]
            case True:
                consume_these      = vals[:end_index]
                pop_count          = len(consume_these)
                data[self.name]    = consume_these
            case 1:
                data[self.name] = self.type_(vals[0])
                pop_count = 1
            case x:
                t = min(x, end_index or len(vals))
                consume_these      = vals[:t]
                pop_count          = len(consume_these)
                data[self.name]    = consume_these

        if 1 < pop_count < self.positional:
            raise doot.errors.DootParseError(
                "Not Enough positional args provided", self.name, self.positional, vals
            )
        elif 1 < self.positional < pop_count:
            raise doot.errors.DootParseError(
                "Too Many positional args provided", self.name, self.positional, vals
            )
        elif 1 < pop_count and self.type_ != list:
            raise doot.errors.DootParseError(
                "Multi positional args should be of type list",
                self.name,
                self.positional,
                self.type_,
            )

        return pop_count

    def maybe_consume(self, args:list[str], data:dict) -> int:
        """
          Given a list of args, possibly add a value to the data.
          operates *in place* on both the args list and the data.
          return True if _consumed a value

          handles:
          ["--arg=val"],
          ["-arg", "val"],
          ["val"],     (if positional=True)
          ["-arg"],    (if type=bool)
          ["-no-arg"], (if type=bool)
        """
        if not bool(args) or data is None or args[0] != self:
            return 0
        if 0 < self._consumed:
            return self._consumed

        pop_count     = 0
        focus         = args[0]
        is_positional = bool(self.positional)

        if is_positional:
            pop_count = self._add_positional_value(data, key=self.name, vals=args)
        else:
            key, vals, pop_count = self._calc_positional_consumption(focus, args)
            self._add_non_positional_value(data, key=key, vals=vals)

        # data has been added, so remove it from the input list
        logging.debug("Arg: %s consuming count %s", self.name, pop_count)
        for x in range(pop_count):
            args.pop(0)

        self._consumed += pop_count
        return self._consumed
