#!/usr/bin/env python3
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
                    TypeGuard, TypeVar, cast, final, overload,
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
from doot._abstract.protocols import Key_p, SpecStruct_p
from doot._structs.code_ref import CodeReference
from doot.utils.chain_get import DootKeyGetter
from doot.utils.decorators import DecorationUtils, DootDecorator
from doot.utils.key_formatter import KeyFormatter

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
EXPANSION_HINT : Final[str]                = "_doot_expansion_hint"
HELP_HINT      : Final[str]                = "_doot_help_hint"

# def __call__(self, **kwargs) -> Any:
# def __format__(self, spec) -> str:
# def format(self, fmt, *, spec=None, state=None) -> str:
# def expand(self, *, fmt=None, spec=None, state=None, on_fail=Any, locs:DootLocations=None, **kwargs) -> Any:
# def within(self, other:str|dict|TomlGuard) -> bool:

class DKey(abc.ABC, Key_p):
    """ A shared, non-functional base class for DootKeys and variants like MultiDKey.
      Use DKey.build for constructing keys
      build takes an 'exp_hint' kwarg dict, which can specialize the expansion

      DootSimpleKeys are strings, wrapped in {} when used in toml.
      so DKey.build("blah") -> SimpleDKey("blah") -> SimpleDKey('blah').form =="{blah}" -> [toml] aValue = "{blah}"

      DootMultiKeys are containers of a string `value`, and a list of SimpleKeys the value contains.
      So DKey.build("{blah}/{bloo}") -> MultiDKey("{blah}/{bloo}", [SimpleDKey("blah", SimpleDKey("bloo")]) -> .form == "{blah}/{bloo}"
    """
    _pattern : ClassVar[re.Pattern] = PATTERN

    @property
    def dec(self):
        raise DeprecationWarning("Use Keyed")

    @abc.abstractmethod
    def __format__(self, spec) -> str:
        pass

    @abc.abstractmethod
    def format(self, fmt, *, spec=None, state=None) -> str:
        pass

    @abc.abstractmethod
    def expand(self, *, fmt=None, spec=None, state=None, on_fail=Any, locs:DootLocations=None, **kwargs) -> Any:
        pass

    @staticmethod
    def build(s:str|DKey|pl.Path|dict, *, strict=False, explicit=False, exp_hint:str|dict=None, help=None) -> DKey:
        """ Make an appropriate DKey based on input value
          Can only create MultiKeys if strict = False,
          if explicit, only keys wrapped in {} are made, everything else is returned untouched
          if strict, then only simple keys can be returned
        """
        # TODO annotate with 'help'
        # TODO store expansion args on build
        match exp_hint:
            case "path":
                is_path = True
            case {"expansion": "path"}:
                is_path = True
            case _:
                is_path = False
        result = s
        match s:
            case { "path": x }:
                result = PathMultiDKey(x)
                exp_hint = "path"
            case pl.Path():
                result = PathMultiDKey(s)
                exp_hint = "path"
            case SimpleDKey() if strict:
                result = s
            case DKey():
                result = s
            case str() if not (s_keys := PATTERN.findall(s)) and not explicit and not is_path:
                result = SimpleDKey(s)
            case str() if is_path and not bool(s_keys):
                result = PathDKey(s)
            case str() if is_path and len(s_keys) == 1 and s_keys[0] == s[1:-1]:
                result = PathDKey(s[1:-1])
            case str() if is_path and len(s_keys) > 1:
                result = PathMultiDKey(s)
            case str() if not s_keys and explicit:
                result = NonDKey(s)
            case str() if len(s_keys) == 1 and s_keys[0] == s[1:-1]:
                result = SimpleDKey(s[1:-1])
            case str() if not strict:
                result = MultiDKey(s)
            case _:
                raise TypeError("Bad Type to build a Doot Key Out of", s)

        if exp_hint is not None:
            result.set_expansion_hint(exp_hint)

        return result

    def set_help(self, help:str):
        setattr(self, HELP_HINT, help)

    def set_expansion_hint(self, etype:str|dict):
        match etype:
            case "str" | "path" | "type" | "redirect" | "redirect_multi":
                setattr(self, EXPANSION_HINT, {"expansion": etype, "kwargs": {}})
            case {"expansion": str(), "kwargs": dict()}:
                setattr(self, EXPANSION_HINT, etype)
            case _:
                raise doot.errors.DootKeyError("Bad Key Expansion Type Declared", self, etype)

    def __call__(self, spec, state):
        """ Expand the key using the registered expansion hint """
        match getattr(self, EXPANSION_HINT, False):
            case False:
                raise doot.errors.DootKeyError("No Default Key Expansion Type Declared", self)
            case {"expansion": "str", "kwargs": kwargs}:
                return self.expand(spec, state, **kwargs)
            case {"expansion": "path", "kwargs": kwargs}:
                return self.to_path(spec, state, **kwargs)
            case {"expansion" : "type", "kwargs" : kwargs}:
                return self.to_type(spec, state, **kwargs)
            case {"expansion": "redirect"}:
                return self.redirect(spec)
            case {"expansion": "redirect_multi"}:
                return self.redirect_multi(spec)
            case {"expansion": "coderef"}:
                return self.to_coderef(spec, state)
            case x:
                raise doot.errors.DootKeyError("Key Called with Bad Key Expansion Type", self, x)

    @property
    def is_indirect(self) -> bool:
        return False

    def within(self, other:str|dict|TomlGuard) -> bool:
        return False

    def keys(self) -> list[DKey]:
        raise NotImplementedError()

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
        return format(str(self), spec)

    def format(self, fmt, *, spec=None, state=None) -> str:
        return self.format(fmt)

    def expand(self, spec=None, state=None, *, on_fail=Any, locs:DootLocations=None, **kwargs) -> str:
        return str(self)

    def within(self, other:str|dict|TomlGuard) -> bool:
        match other:
            case str():
                return self.form in other
            case dict() | TomlGuard():
                return self in other
            case _:
                raise TypeError("Unknown DKey target for within", other)

    @ftz.cached_property
    def indirect(self) -> DKey:
        if not self.is_indirect:
            return SimpleDKey("{}_".format(super().__str__()))
        return self

    @property
    def is_indirect(self):
        return False

class SimpleDKey(str, DKey):
    """
      A Single key with no extras.
      ie: {x}. not {x}{y}, or {x}.blah.
    """

    def __repr__(self):
        return "<SimpleDKey: {}>".format(str(self))

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        match other:
            case DKey() | str():
                return str(self) == str(other)
            case _:
                return False

    def __call__(self, **kwargs) -> Any:
        raise NotImplementedError()

    def __format__(self, spec):
        return format(self.form, spec)

    def format(self, fmt, * spec=None, state=None) -> str:
        return self.expand(*args, **kwargs)

    def expand(self, *, fmt=None, spec=None, state=None, on_fail=Any, locs:DootLocations=None, **kwargs) -> Any:
        key = self.format("{!_}", spec=spec)
        try:
            return KeyFormatter.fmt(key, _spec=spec, _state=state, _rec=rec, _locs=locs, _insist=insist)
        except (KeyError, TypeError) as err:
            if on_fail != Any:
                return on_fail
            else:
                raise err

    @ftz.cached_property
    def is_indirect(self):
        return str(self).endswith("_")

    def within(self, other:str|dict|TomlGuard) -> bool:
        match other:
            case str():
                return self.form in other
            case dict() | TomlGuard():
                return self in other
            case _:
                raise TypeError("Uknown DKey target for within", other)

class PathDKey(SimpleDKey):
    """ A Key that always expands as a str of a path """

    def expand(self, spec=None, state=None, *, on_fail=Any, locs=None, **kwargs) -> str:
        return str(self.to_path(spec, state, chain=chain, on_fail=on_fail, locs=locs))

    def __repr__(self):
        return "<PathDKey: {}>".format(str(self))

    def __call__(self, spec, state):
        """ Expand the key using the registered expansion hint """
        match getattr(self, EXPANSION_HINT, False):
            case False:
                return self.to_path(spec, state)
            case {"expansion": "str", "kwargs": kwargs}:
                return self.expand(spec, state, **kwargs)
            case {"expansion": "path", "kwargs": kwargs}:
                return self.to_path(spec, state, **kwargs)
            case {"expansion": "redirect"}:
                return self.redirect(spec)
            case {"expansion": "redirect_multi"}:
                return self.redirect_multi(spec)
            case x:
                raise doot.errors.DootKeyError("Key Called with Bad Key Expansion Type", self, x)

class ArgsDKey(str, DKey):
    """ A Key representing the action spec's args """

    def __call__(self, spec, state, **kwargs):
        return self.to_type(spec, state)

    def __repr__(self):
        return "<ArgsDKey>"

    def expand(self, *args, **kwargs):
        raise doot.errors.DootKeyError("Args Key doesn't expand")

class KwargsDKey(ArgsDKey):
    """ A Key representing all of an action spec's kwargs """

    def __repr__(self):
        return "<ArgsDKey>"

    def to_type(self, spec:None|SpecStruct_p=None, state=None, *args, **kwargs) -> dict:
        match spec:
            case _ if hasattr(spec, "params"):
                return spec.params
            case None:
                return {}

class MultiDKey(DKey):
    """ A string or path of multiple keys """

    def __init__(self, val:str|pl.Path):
        self.value : str|pl.Path        = val
        self._keys : set[SimpleDKey] = set(SimpleDKey(x) for x in PATTERN.findall(str(val)))

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "<MultiDKey: {}>".format(str(self))

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        match other:
            case DKey() | str() | pl.Path():
                return str(self) == str(other)
            case _:
                return False

    def keys(self) -> set(SimpleDKey):
        return self._keys

    def expand(self, spec=None, state=None, *, on_fail=Any, locs=None, **kwargs) -> str:
        try:
            return KeyFormatter.fmt(self.value, _spec=spec, _state=state, _rec=rec, _insist=insist, _locs=locs)
        except (KeyError, TypeError) as err:
            if bool(chain):
                return chain[0].expand(spec, state, rec=rec, chain=chain[1:], on_fail=on_fail)
            elif on_fail != Any:
                return on_fail
            else:
                raise err

    def within(self, other:str|dict|TomlGuard) -> bool:
        return str(self) in other

class PathMultiDKey(MultiDKey):
    """ A MultiKey that always expands as a str of a path """

    def expand(self, spec=None, state=None, *, rec=False, insist=False, chain:list[DKey]=None, on_fail=Any, locs=None, **kwargs) -> str:
        return str(self.to_path(spec, state, chain=chain, on_fail=on_fail, locs=locs))

    def __repr__(self):
        return "<PathMultiDKey: {}>".format(str(self))

    def __call__(self, spec, state):
        """ Expand the key using the registered expansion hint """
        match getattr(self, EXPANSION_HINT, False):
            case False:
                return self.to_path(spec, state)
            case {"expansion": "str", "kwargs": kwargs}:
                return self.expand(spec, state, **kwargs)
            case {"expansion": "path", "kwargs": kwargs}:
                return self.to_path(spec, state, **kwargs)
            case {"expansion": "redirect"}:
                return self.redirect(spec)
            case {"expansion": "redirect_multi"}:
                return self.redirect_multi(spec)
            case x:
                raise doot.errors.DootKeyError("Key Called with Bad Key Expansion Type", self, x)

class ImportDKey(SimpleDKey):
    """ a key to specify a key is used for importing
    ie: str expands -> CodeReference.build -> .try_import
    """
    pass
