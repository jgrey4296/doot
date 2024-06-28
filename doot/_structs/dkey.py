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
from doot._structs.task_name import TaskName
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
CHECKTYPE      : TypeAlias                 = None|type|types.GenericAlias|types.UnionType
MARKTYPE       : TypeAlias                 = None|str|type|DKeyMark_e

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
    """ A shared base class for DKeys and variants.
      Implements __new__ to create the correct key type, from a string, dynamically.

      kwargs:
      explicit = insists that keys in the string are wrapped in braces '{akey} {anotherkey}'.
      mark     = pre-register expansion parameters / type etc
      check    = dictate a type that expanding this key must match
      fparams  = str formatting instructions for the key

      Eg:
      DKey('blah')
      -> SingleDKey('blah')
      -> SingleDKey('blah').format('w')
      -> '{blah}'
      -> [toml] aValue = '{blah}'

      Because cls.__new__ calls __init__ automatically for return values of type cls,
      DKey is the factory, but all DKeys are subclasses of DKeyBase,
      to allow control over __init__.
      """
    mark = DKeyMark_e

    def __new__(cls, data:str|DKey|pl.Path|dict, *, explicit=False, fparams=None, mark:MARKTYPE=None, **kwargs) -> DKey:
        if isinstance(data, DKey):
            return data

        s_keys           = DKeyFormatter.Parse(data)
        data, fparams = data, fparams or ""

        # TODO handle conversion parameters in data

        # Discriminate by mark:
        ctor = SingleDKey
        match mark:
            case _ if explicit and len(s_keys) < 1:
                ctor =  NonDKey
            case None | DKeyMark_e.STR | DKeyMark_e.FREE if 1 < len(s_keys):
                ctor =  MultiDKey
            case DKeyMark_e.STR:
                ctor =  SingleDKey
            case DKeyMark_e.PATH:
                ctor =  PathMultiDKey
            case DKeyMark_e.REDIRECT:
                ctor =  RedirectionDKey
            case DKeyMark_e.CODE:
                ctor =  ImportDKey
            case DKeyMark_e.TASK:
                ctor =  SingleDKey
            case DKeyMark_e.ARGS:
                ctor =  ArgsDKey
            case DKeyMark_e.KWARGS:
                ctor =  KwargsDKey
            case DKeyMark_e.POSTBOX:
                ctor =  SingleDKey
            case DKeyMark_e.NULL:
                ctor =  NonDKey
            case type() if mark is pl.Path:
                ctor =  PathMultiDKey
            case type():
                ctor =  SingleDKey

        if not issubclass(ctor, MultiDKey) and  len(s_keys) < 2:
            data, _, fparams = data.removeprefix("{").removesuffix("}").partition(":")

        # Build the key from ctor + init it
        result           = str.__new__(ctor, data)
        result.__init__(data, fparams=fparams, mark=mark, **kwargs)

        return result

##-- end meta

##-- expansion and formatting

class DKeyFormatting_m:

    """ General formatting for dkeys """

    def format(self, fmt, *, spec=None, state=None) -> str:
        return DKeyFormatter.fmt(self, fmt)

class DKeyExpansion_m:
    """ general expansion for dkeys """

    def expand(self, *sources, fmt=None, on_fail=None, **kwargs) -> Any:
        expanded = DKeyFormatter.expand(self, sources=sources)
        result   = None
        match expanded:
            case None:
                result = on_fail or self._exp_fallback
            case _:
                result = self._exp_type(expanded)

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
                pass

##-- end expansion and formatting

class DKeyBase(DKeyFormatting_m, DKeyExpansion_m, Key_p, str):
    """
      Base class characteristics of DKeys.
      adds:
      `_mark`
      `_exp_type`
      `_typecheck`

      plus some util methods

    """

    _mark         : DKeyMark_e                  = DKey.mark.default
    _exp_type     : type|callable               = str
    _typecheck    : CHECKTYPE                   = Any
    _exp_fallback : Any                         = None
    _fparams      : None|str                    = None
    _help         : None|str                    = None

    __hash__                                    = str.__hash__

    def __new__(cls, *args, **kwargs):
        """ Blocks creation of DKey's except through DKey itself,
          unless 'force=True' kwarg (for testing).
        """
        if not kwargs.get('force', False):
            raise RuntimeError("Don't build DKey subclasses directly")
        del kwargs['force']
        obj = str.__new__(cls, *args)
        obj.__init__(*args, **kwargs)
        return obj

    def __init__(self, data, fparams:None|str=None, check:CHECKTYPE=None, help:None|str=None, mark:MARKTYPE=None, fallback=None, **kwargs):
        super().__init__(data)
        self.set_expansion(mark, check)
        self.set_fparams(fparams)
        self.set_help(help)
        self._exp_fallback = fallback

    def __call__(self, *args, **kwargs) -> Any:
        return self.expand(*args, **kwargs)

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

    def set_help(self, help:None|str) -> Self:
        match help:
            case None:
                pass
            case str():
                self._help = help

        return self

    def set_fparams(self, params:str) -> Self:
        match params:
            case None:
                pass
            case str() if bool(params):
                self._fparams = params
        return self

    def set_expansion(self, mark:MARKTYPE, check:CHECKTYPE) -> Self:
        """ pre-register expansion parameters """
        self._mark = mark
        match mark:
            case None | DKeyMark_e.FREE:
                self._exp_type  = identity
                self._typecheck = check or Any
            case DKeyMark_e.NULL | DKeyMark_e.STR:
                self._exp_type  = str
                self._typecheck = str
            case str():
                self._mark = DKeyMark_e.FREE
                # Try to build a DKeyMark_e, then recurse

                # else try making a coderefer from it
                raise NotImplementedError()
            case DKeyMark_e.PATH:
                self._exp_type  = pl.Path
                self._typecheck = pl.Path
            case DKeyMark_e.REDIRECT:
                self._exp_type  = DKey
                self._typecheck = DKey
            case DKeyMark_e.CODE:
                self._exp_type  = CodeReference.build
                self._typecheck = CodeReference
            case DKeyMark_e.TASK:
                self._exp_type  = TaskName.build
                self._typecheck = TaskName
            case DKeyMark_e.ARGS:
                self._exp_type  = list
                self._typecheck = list
            case DKeyMark_e.KWARGS:
                self._exp_type  = dict
                self._typecheck = dict
            case DKeyMark_e.POSTBOX:
                self._exp_type  = list
                self._typecheck = check or list
            case type() if issubclass(mark, Buildable_p):
                self._mark = DKeyMark_e.FREE
                self._exp_type  = mark.build
                self._typecheck = check or mark
            case type():
                self._mark = DKeyMark_e.FREE
                self._exp_type  = mark
                self._typecheck = check or mark
            case _:
                raise doot.errors.DootKeyError("Bad Key Expansion Type Declared", self, etype)

        return self

    def keys(self) -> list:
        return []

##-- core

class SingleDKey(DKeyBase):
    """
      A Single key with no extras.
      ie: {x}. not {x}{y}, or {x}.blah.
    """

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

class MultiDKey(DKeyBase):

    def __init__(self, data:str|pl.Path, *, mark:MARKTYPE=None, **kwargs):
        super().__init__(data, mark=mark, **kwargs)
        s_keys           = DKeyFormatter.Parse(data)
        self._subkeys    = [DKey(x[0], fparams=x[1], mark=x[2]) for x in s_keys]
        assert(bool(self._subkeys))

    def __format__(self, spec:str):
        """
          Multi keys have no special formatting

          ... except stripping dkey particular format specs out of the result?
        """
        rem, wrap, direct = self._consume_format_params(spec)
        return format(str(self), rem)

    def keys(self):
        return self._subkeys

    def expand(self, *sources, fmt=None, on_fail=None, **kwargs) -> Any:
        """ Expand subkeys, format the multi key
          Takes a variable number of sources (dicts, tomlguards, specs, dootlocations..)
        """
        expanded = DKeyFormatter.expand(self, sources=sources)
        match self._exp_type(expanded):
            case pl.Path() as x:
                return doot.locs[x]
            case str() as x:
                return x
            case x:
                return x

class NonDKey(DKeyBase):
    """
      Just a string, not a key. But this lets you call no-ops for key specific methods
    """
    _mark = DKey.mark.NULL

    def __init__(self, data, **kwargs):
        """
          ignores all kwargs
        """
        super().__init__(data)

    def __format__(self, spec) -> str:
        rem, _, _ = self._consume_format_params(spec)
        return format(str(self), rem)

    def format(self, fmt) -> str:
        return format(self, fmt)

    def expand(self, *args, **kwargs) -> str:
        return str(self)

##-- end core

##-- subclasses

class RedirectionDKey(SingleDKey):
    """
      A Key for getting a redirected key.
      eg: RedirectionDKey(key_) -> SingleDKey(value)
    """

    _mark = DKey.mark.REDIRECT

    def expand(self, *sources, on_fail=None, **kwargs):
        expanded = DKeyFormatter.redirect(self, sources=sources)
        result = None
        match expanded:
            case None:
                result = on_fail or self._exp_fallback
            case _:
                result = self._exp_type(expanded)

        self._check_expansion(result)
        return result


class ArgsDKey(SingleDKey):
    """ A Key representing the action spec's args """
    _mark = DKey.mark.ARGS

class KwargsDKey(SingleDKey):
    """ A Key representing all of an action spec's kwargs """

    _mark = DKey.mark.KWARGS

class ImportDKey(SingleDKey):
    """
      Subclass for dkey's which expand to CodeReferences
    """
    _mark = DKey.mark.CODE

class PathMultiDKey(MultiDKey):
    """
    A MultiKey that always expands as a path
    """
    _mark = DKey.mark.PATH

class PostBoxDKey(SingleDKey):
    """ A DKey which expands from postbox tasknames  """
    _mark = DKey.mark.POSTBOX

    def expand(self, *sources, on_fail=None, **kwargs):
        # expand key to a task name
        target = None
        # get from postbox
        result = None
        self._check_expansion(result)
        # return result
        raise NotImplementedError()



##-- end subclasses
