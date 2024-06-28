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
from doot.enums import DKeyMark_e
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
CHECKTYPE      : TypeAlias =               None|type|types.GenericAlias|types.UnionType

def identity(x):
    return x

##-- meta

class DKeyMeta(type(str)):
    """
      The Metaclass for keys, which ensures that subclasses of DKeyBase
      are DKey's, despite there not being an actual subclass relation between them
    """

    def __instancecheck__(cls, instance):
        return any(x.__instancecheck__(instance) for x in {DKeyBase})

    def __subclasscheck__(cls, sub):
        candidates = {DKeyBase}
        return any(x in candidates for x in sub.mro())

class DKey(metaclass=DKeyMeta):
    """ A shared, non-functional base class for DootKeys and variants like MultiDKey.
      Use DKey.build for constructing keys
      build takes an 'exp_hint' kwarg dict, which can specialize the expansion

      DootSimpleKeys are strings, wrapped in {} when used in toml.
      so DKey.build('blah') -> SingleDKey('blah') -> SingleDKey('blah').form =='{blah}' -> [toml] aValue = '{blah}'

      DootMultiKeys are containers of a string `value`, and a list of SimpleKeys the value contains.
      So DKey.build('{blah}/{bloo}') -> MultiDKey('{blah}/{bloo}', [SingleDKey('blah', SingleDKey('bloo')]) -> .form == '{blah}/{bloo}'
      """
    mark = DKeyMark_e

    def __new__(cls, data:str|DKey|pl.Path|dict, *, explicit=False, fparams=None, check:CHECKTYPE=None, ehint:type|str|None=None, help=None, mark:DKeyMark_e=None) -> DKey:
        result = data
        match data:
            case DKey(): # already a dkey, return
                return data
            case str() if len(s_keys := DKeyFormatter.Parse(data)) == 1: # one explicit key
                data, _, fparams = data.removeprefix("{").removesuffix("}").partition(":")
                result = str.__new__(SingleDKey, data)
                result.__init__(data, fparams=fparams, ehint=ehint, check=check, help=help)
            case str() if not bool(s_keys) and explicit: # no subkeys, {explicit} mandated
                result = str.__new__(NonDKey, data)
                result.__init__(data)
            case str() if bool(s_keys): # {subkeys} found
                result = str.__new__(MultiDKey, data)
                subkeys = [DKey(x[0], fparams=x[1], ehint=x[2]) for x in s_keys]
                result.__init__(data, subkeys=subkeys, ehint=ehint)
            case str():
                result = str.__new__(SingleDKey, data)
                result.__init__(data, fparams=fparams, ehint=ehint, check=check, help=help)
            case _:
                raise TypeError("Bad Type to build a Doot Key Out of", s)

        return result

##-- end meta

##-- expansion and formatting

class DKeyFormatting_m:

    """ General formatting for dkeys """

    def format(self, fmt, *, spec=None, state=None) -> str:
        return DKeyFormatter.fmt(self, fmt)

class DKeyExpansion_m:
    """ general expansion for dkeys """

    def expand(self, *, fmt=None, spec=None, state=None, on_fail=None, locs:DootLocations=None, **kwargs) -> Any:
        expanded = DKeyFormatter.expand(self, spec=spec, state=state, locs=locs)
        result   = None
        match expanded:
            case None:
                result = on_fail
            case _:
                result = self._etype(expanded)

        self._check_expansion(result)
        match result:
            case pl.Path() as x:
                return doot.locs[x]
            case str() as x:
                return x
            case x:
                return x

    def _check_expansion(self, value):
        """ typecheck an expansion result """
        match self._typecheck:
            case x if x is Any:
                pass
            case types.GenericAlias():
                if not isinstance(value, self._typecheck.__origin__):
                    raise TypeError("Expansion value is not the correct container", self._typecheck, value, self)
                if len((args:=self._typecheck.__args__)) == 1 and not all(isinstance(x, args[0]) for x in value):
                    raise TypeError("Expansion value does not contain the correct value types", self._typecheck, value, self)

            case types.UnionType() if not isinstance(value, self._typecheck):
                raise TypeError("Expansion value does not match required type", self._typecheck, value, self)
            case type() if not isinstance(value, self._typecheck):
                raise TypeError("Expansion value does not match required type", self._typecheck, value, self)
            case _:
                raise TypeError("Unkown type specified for expansion type constraint", self._typecheck)

##-- end expansion and formatting

class DKeyBase(DKeyFormatting_m, DKeyExpansion_m, Key_p, str):

    def __new__(cls, *args, **kwargs):
        """ Blocks creation of DKey's except through DKey itself """
        if not kwargs.get('force', False):
            raise RuntimeError("Don't build DKey subclasses directly")
        del kwargs['force']
        obj = str.__new__(cls, *args)
        obj.__init__(*args, **kwargs)
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self}>"

    def __and__(self, other) -> bool:
        match other:
            case MultiDKey():
                return f"{self:w}" in other._subkeys
            case str():
                return f"{self:w}" in other

    def __rand__(self, other):
        return self & other

    def __eq__(self, other):
        match other:
            case DKey() | str():
                return str(self) == str(other)
            case _:
                return False

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
            case type() if issubclass(etype, Buildable_p):
                self._etype = etype.build
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

    def set_typecheck(self, check:CHECKTYPE) -> Self:
        match check:
            case None:
                self._typecheck = Any
            case type() | types.GenericAlias() | types.UnionType():
                self._typecheck = check
            case _:
                raise TypeError("Bad TypeCheck type", check)
        return self

    def _consume_format_params(self, spec:str) -> tuple(str, bool, bool, bool):
        """
          return (consumed, wrap, direct)
        """
        wrap     = 'w' in spec
        indirect = 'i' in spec
        direct   = 'd' in spec
        remaining = FMT_PATTERN.sub("", spec)
        assert(not (direct and indirect))
        return remaining, wrap, (direct or (not indirect))

##-- core

class NonDKey(DKeyBase):
    """
      Just a string, not a key. But this lets you call no-ops for key specific methods
    """

    __hash__ = str.__hash__

    def __init__(self, data, **kwargs):
        super().__init__()
        self.set_fparams(None)
        self.set_ehint(None)
        self.set_help(None)
        self.set_typecheck(None)

    def __call__(self, *args, **kwargs) -> str:
        return str(self)

    def __format__(self, spec) -> str:
        rem, _, _ = self._consume_format_params(spec)
        return format(str(self), rem)

    def format(self, fmt, *, spec=None, state=None) -> str:
        return self.format(fmt)

    def expand(self, *, fmt=None, spec=None, state=None, on_fail=None, locs:DootLocations=None) -> str:
        return str(self)

    @property
    def _keys(self) -> list:
        return []

class SingleDKey(DKeyBase):
    """
      A Single key with no extras.
      ie: {x}. not {x}{y}, or {x}.blah.
    """

    __hash__ = str.__hash__

    def __init__(self, data, fparams:None|str=None, ehint:None|str=None, check:CHECKTYPE=None, help:None|str=None, **kwargs):
        super().__init__()
        self.set_fparams(fparams)
        self.set_ehint(ehint)
        self.set_help(help)
        self.set_typecheck(check)

    # def __repr__(self):
    #     return "<SingleDKey: {}>".format(str(self))

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
        rem, wrap, direct = self._consume_format_params(spec)

        # format
        result = str(self)
        if direct:
            result = result.removesuffix("_")
        elif not result.endswith("_"):
            result = f"{result}_"

        if wrap:
            result = "".join(["{", result, "}"])

        return format(result, rem)

    @property
    def _keys(self) -> list[DKey]:
        return []

class MultiDKey(DKeyBase):

    __hash__ = str.__hash__

    def __init__(self, data, *, subkeys:list[DKey]|set[DKey]=None, ehint:None|type=None, **kwargs):
        assert(bool(subkeys))
        super().__init__()
        self._subkeys = subkeys
        self.set_fparams(None)
        self.set_ehint(ehint)
        self.set_help(None)
        self.set_typecheck(None)

    def __call__(self, **kwargs) -> Any:
        raise NotImplementedError()

    def __format__(self, spec:str):
        """
          Multi keys have no special formatting

          ... except stripping dkey particular format specs out of the result?
        """
        rem, wrap, direct = self._consume_format_params(spec)
        return format(str(self), rem)

    def keys(self):
        return self._subkeys

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

##-- end core

##-- subclasses

class RedirectionDKey(SingleDKey):
    """
      A Key for getting a redirected key.
      eg: RedirectionDKey(key_) -> SingleDKey(value)
    """
    pass
class ArgsDKey(SingleDKey):
    """ A Key representing the action spec's args """

    def __call__(self, spec, state, **kwargs):
        return self.to_type(spec, state)

    def __repr__(self):
        return "<ArgsDKey>"

    def expand(self, *args, **kwargs):
        raise doot.errors.DootKeyError("Args Key doesn't expand")

class KwargsDKey(SingleDKey):
    """ A Key representing all of an action spec's kwargs """

    def __repr__(self):
        return "<ArgsDKey>"

    def to_type(self, spec:None|SpecStruct_p=None, state=None, *args, **kwargs) -> dict:
        match spec:
            case _ if hasattr(spec, "params"):
                return spec.params
            case None:
                return {}

class ImportDKey(SingleDKey):
    """
      Subclass for dkey's which expand to CodeReferences
    """
    pass

class PathMultiDKey(MultiDKey):
    """
    A MultiKey that always expands as a path
    """
    pass

class PostBoxDKey(SingleDKey):
    """ A DKey which expands from postbox tasknames  """
    pass
##-- end subclasses
