#!/usr/bin/env python2
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import string
import time
import types
import weakref
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload, Self,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import decorator
import more_itertools as mitz
from pydantic import BaseModel, Field, field_validator, model_validator
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import Key_p, SpecStruct_p, Buildable_p
from doot._structs.code_ref import CodeReference
from doot.utils.chain_get import DootKeyGetter
from doot.utils.decorators import DecorationUtils, DootDecorator
from doot.utils.dkey_formatter import DKeyFormatter

# ##-- end 1st party imports

##-- type checking
if TYPE_CHECKING:
    DootLocations:TypeAlias = Any
    DootKey:TypeAlias = Key_p
##-- end type checking

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

KEY_PATTERN                                = doot.constants.patterns.KEY_PATTERN
MAX_KEY_EXPANSIONS                         = doot.constants.patterns.MAX_KEY_EXPANSIONS
STATE_TASK_NAME_K                          = doot.constants.patterns.STATE_TASK_NAME_K

PATTERN        : Final[re.Pattern]         = re.compile(KEY_PATTERN)
FAIL_PATTERN   : Final[re.Pattern]         = re.compile("[^a-zA-Z_{}/0-9-]")
FMT_PATTERN    : Final[re.Pattern]         = re.compile("[wdi]+")
EXPANSION_HINT : Final[str]                = "_doot_expansion_hint"
HELP_HINT      : Final[str]                = "_doot_help_hint"

def identity(x):
    return x

class DKeyFactory_m(Buildable_p):

    @staticmethod
    def build(s:str|DKey|pl.Path|dict, *, explicit=False, ehint:type|str|None=None, help=None) -> DKey:
        """ Make an appropriate DKey based on input value
          if explicit, only keys wrapped in {} are made, everything else is returned untouched
          ehint sets expansion parameters
        """
        result = s
        match s:
            case DKey(): # already a dkey, return
                return s
            case str() if len(s_keys := DKeyFormatter.Parse(s)) == 1: # one explicit key
                result = SimpleDKey(s)
            case str() if not bool(s_keys) and explicit: # no subkeys, {explicit} mandated
                result = NonDKey(s)
            case str() if bool(s_keys): # {subkeys} found
                result = MultiDKey(s)
            case str():
                result = SimpleDKey(s)
            case _:
                raise TypeError("Bad Type to build a Doot Key Out of", s)

        result.set_ehint(ehint)
        result.set_help(help)
        return result

    def set_help(self, help:None|str) -> Self:
        match help:
            case None:
                return
            case str:
                self._help = help

        return self

    def set_ehint(self, etype:None|str|dict) -> Self:
        """ pre-register expansion parameters """
        match etype:
            case None | "":
                self._etype = identity
            case "str":
                self._etype = str
            case "path":
                self._etype = pl.Path
            case "key":
                self._etype = DKey.build
            case type():
                self._etype = etype
            case _:
                raise doot.errors.DootKeyError("Bad Key Expansion Type Declared", self, etype)

        return self

    def set_fparams(self, params:str) -> Self:
        self._fparams = params
        return self

class DKeyFormatting_m:

    def format(self, fmt, *, spec=None, state=None) -> str:
        return DKeyFormatter.fmt(self, fmt)

class DKeyExpansion_m:

    def expand(self, *, fmt=None, spec=None, state=None, on_fail=None, locs:DootLocations=None, **kwargs) -> Any:
        expanded = DKeyFormatter.expand(self, spec=spec, state=state, locs=locs)
        if expanded is None:
            return on_fail

        match self._etype(expanded):
            case pl.Path() as x:
                return doot.locs[x]
            case str() as x:
                return x
            case x:
                return x

class DKey(abc.ABC, DKeyFactory_m, DKeyExpansion_m, DKeyFormatting_m, Key_p):
    """ A shared, non-functional base class for DootKeys and variants like MultiDKey.
      Use DKey.build for constructing keys
      build takes an 'exp_hint' kwarg dict, which can specialize the expansion

      DootSimpleKeys are strings, wrapped in {} when used in toml.
      so DKey.build("blah") -> SimpleDKey("blah") -> SimpleDKey('blah').form =="{blah}" -> [toml] aValue = "{blah}"

      DootMultiKeys are containers of a string `value`, and a list of SimpleKeys the value contains.
      So DKey.build("{blah}/{bloo}") -> MultiDKey("{blah}/{bloo}", [SimpleDKey("blah", SimpleDKey("bloo")]) -> .form == "{blah}/{bloo}"
    """
    _pattern : ClassVar[re.Pattern] = PATTERN

    @abc.abstractmethod
    def __format__(self, spec) -> str:
        pass

    @abc.abstractmethod
    def format(self, fmt, *, spec=None, state=None) -> str:
        pass

    def keys(self) -> list[DKey]:
        return self._keys

    @property
    @abc.abstractmethod
    def _keys(self) -> list[DKey]:
        pass

    @property
    def is_indirect(self) -> bool:
        return False

    def within(self, other:str|dict|TomlGuard) -> bool:
        return False

class NonDKey(str, DKey):
    """
      Just a string, not a key. But this lets you call no-ops for key specific methods
    """

    def __repr__(self):
        return "<NonDKey: {}>".format(str(self))

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        match other:
            case DKey() | str():
                return str(self) == str(other)
            case _:
                return False

    def __call__(self, *args, **kwargs) -> str:
        return str(self)

    def __format__(self, spec) -> str:
        return format(str(self), spec.replace("d","").replace("w","").replace("i",""))

    def format(self, fmt, *, spec=None, state=None) -> str:
        return self.format(fmt)

    def expand(self, *, fmt=None, spec=None, state=None, on_fail=None, locs:DootLocations=None) -> str:
        return str(self)

    def within(self, other:str|dict|TomlGuard) -> bool:
        match other:
            case str():
                return self.form in other
            case dict() | TomlGuard():
                return self in other
            case _:
                raise TypeError("Unknown DKey target for within", other)

    @property
    def is_indirect(self):
        return False

    @property
    def _keys(self) -> list:
        return []

class SimpleDKey(str, DKey):
    """
      A Single key with no extras.
      ie: {x}. not {x}{y}, or {x}.blah.
    """

    def __new__(cls, data):
        keys = set(x[0] for x in DKeyFormatter.Parse(data))
        if 1 < len(keys):
            raise ValueError("Simple Keys should not have subkeys")
        data, _, fparams = data.removeprefix("{").removesuffix("}").partition(":")
        obj = super().__new__(cls, data)
        obj.set_fparams(fparams)
        return obj

    def __hash__(self):
        return super().__hash__()

    def __repr__(self):
        return "<SimpleDKey: {}>".format(str(self))

    def __eq__(self, other):
        match other:
            case DKey() | str():
                return str(self) == str(other)
            case _:
                return False

    def __call__(self, **kwargs) -> Any:
        raise NotImplementedError()

    def __format__(self, spec:str) -> str:
        """
          Extends standard string format spec language:
            [[fill]align][sign][z][#][0][width][grouping_option][. precision][type]
            (https://docs.python.org/3/library/string.html#format-specification-mini-language)

          Using the # alt form to declare keys are wrapped.
          eg: for key = DKey('test'), ikey = DKey('test_')
          f'{key}'   -> 'test'
          f'{key:w}' -> '{test}'
          f'{key:i}  ->  'test_'
          f'{key:wi} -> '{test_}'

          f'{ikey:d} -> 'test'

        """
        if not bool(spec):
            return str(self)
        wrap     = 'w' in spec
        indirect = 'i' in spec
        direct   = 'd' in spec
        remaining = FMT_PATTERN.sub("", spec)
        assert(not (direct and indirect))

        # format
        result = str(self)
        if direct:
            result = result.removesuffix("_")
        elif indirect and not result.endswith("_"):
            result = f"{result}_"

        if wrap:
            result = "".join(["{", result, "}"])

        return format(result, remaining)

    @ftz.cached_property
    def is_indirect(self):
        return self.endswith("_")

    def within(self, other:str|dict|TomlGuard) -> bool:
        match other:
            case str():
                return self.form in other
            case dict() | TomlGuard():
                return self in other
            case _:
                raise TypeError("Uknown DKey target for within", other)

    @property
    def _keys(self) -> list[DKey]:
        return []

class MultiDKey(str, DKey):

    def __new__(cls, data):
        obj = super().__new__(cls, data)
        return obj

    def __hash__(self):
        return super().__hash__()

    def __repr__(self):
        return "<MultiDKey: {}>".format(str(self))

    def __eq__(self, other):
        match other:
            case DKey() | str():
                return str(self) == str(other)
            case _:
                return False

    def __call__(self, **kwargs) -> Any:
        raise NotImplementedError()

    def __format__(self, spec:str):
        """
          Multi keys have no special formatting

          ... except stripping dkey particular format specs out of the result?
        """
        return str(self)

    @ftz.cached_property
    def is_indirect(self):
        """ Multi keys can't be indirect """
        return False

    def within(self, other:str|dict|TomlGuard) -> bool:
        match other:
            case str():
                return self.form in other
            case dict() | TomlGuard():
                return self in other
            case _:
                raise TypeError("Uknown DKey target for within", other)

    def keys(self):
        return self._keys

    @ftz.cached_property
    def _keys(self) -> list[DKey]:
        keys = set()
        for data in DKeyFormatter.Parse(self):
            keys.add(SimpleDKey(data[0]).set_fparams(data[1]).set_ehint(data[2]))
        if not bool(keys):
            raise ValueError("MultiDKey's must have subkeys", self)
        return list(keys)

    def expand(self, *, fmt=None, spec=None, state=None, on_fail=None, locs:DootLocations=None, **kwargs) -> Any:
        """ Expand subkeys, format the multi key  """
        expanded = DKeyFormatter.expand(self, spec=spec, state=state, locs=locs)
        match self._etype(expanded):
            case pl.Path() as x:
                return doot.locs[x]
            case str() as x:
                return x
            case x:
                return x
