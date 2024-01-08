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
# from dataclasses import InitVar, dataclass, field
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

import abc
from collections import UserString
import string
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.constants import KEY_PATTERN, MAX_KEY_EXPANSIONS
from doot._structs.action_spec import DootActionSpec
from doot._structs.artifact import DootTaskArtifact

PATTERN      : Final[re.Pattern]    = re.compile("{(.+?)}")
FAIL_PATTERN : Final[re.Pattern]    = re.compile("[^a-zA-Z_{}/0-9-]")

class DootFormatter(string.Formatter):
    """
      A Formatter for expanding arguments based on action spec kwargs, and task state, and cli args
    """
    _fmt = None

    def fmt() -> DootFormatter:
        if not DootFormatter._fmt:
            DootFormatter._fmt = DootFormatter()

        return DootFormatter._fmt

    def format(self, fmt:str|DootKey|pl.Path, /, *args, _as_path=False, **kwargs) -> str:
        self._depth = 0
        match kwargs.get("_spec", None):
            case None:
                kwargs['_spec'] = {}
            case DootActionSpec():
                kwargs['_spec'] = kwargs['_spec'].kwargs
            case x:
                raise TypeError("Bad Spec Type in Format Call", x)

        match fmt:
            case DootKey():
                fmt = fmt.form
                result = self.vformat(fmt, args, kwargs)
            case str():
                result = self.vformat(fmt, args, kwargs)
            # case pl.Path():
            #     result = str(ftz.reduce(pl.Path.joinpath, [self.vformat(x, args, kwargs) for x in fmt.parts], pl.Path()))
            case _:
                raise TypeError("Unrecognized expansion type", fmt)

        return result

    def get_value(self, key, args, kwargs):
        logging.debug("Expanding: %s", key)
        if isinstance(key, int):
            return args[key]

        spec              = kwargs.get('_spec')
        state             = kwargs.get('_state', None) or {}
        cli               = doot.args.on_fail({}).tasks[str(state.get('_task_name', None))]()
        replacement       = cli.get(key, None) or state.get(key, None) or spec.get(key, None)
        match replacement:
            case None:
                return DootKey.make(key).form
            case DootKey() if self._depth < MAX_KEY_EXPANSIONS:
                self._depth += 1
                return self.vformat(replacement.form, args, kwargs)
            case str() if kwargs.get("_rec", False) and self._depth < MAX_KEY_EXPANSIONS:
                self._depth += 1
                return self.vformat(str(replacement), args, kwargs)
            case str():
                return replacement
            case pl.Path() if self._depth < MAX_KEY_EXPANSIONS:
                self._depth += 1
                return ftz.reduce(pl.Path.joinpath, map(lambda x: self.vformat(x, args, kwargs), replacement.parts), pl.Path())
            case _:
                return str(replacement)
                # raise TypeError("Replacement Value isn't a string", args, kwargs)

class DootKey(abc.ABC):
    """ A shared, non-functional base class for DootKeys and variants like DootMultiKey.
      Use DootKey.make for constructing keys

      DootSimpleKeys are strings, wrapped in {} when used in toml.
      so DootKey.make("blah") -> DootSimpleKey("blah") -> DootSimpleKey('blah').form =="{blah}" -> [toml] aValue = "{blah}"

      DootMultiKeys are containers of a string `value`, and a list of SimpleKeys the value contains.
      So DootKey.make("{blah}/{bloo}") -> DootMultiKey("{blah}/{bloo}", [DootSimpleKey("blah", DootSimpleKey("bloo")]) -> .form == "{blah}/{bloo}"
    """

    @staticmethod
    def make(s:str|DootKEy|DootTaskArtifact|pl.Path, *, strict=False, explicit=False) -> DootKey:
        """ Make an appropriate DootKey based on input value
          Can only create MultiKeys if strict = False,
          if explicit, only keys wrapped in {} are made, everything else is returned untouched
        """
        match s:
            case DootKey():
                return s
            case str() if strict and (s.isnumeric() or not s.isascii()):
                raise ValueError("Bad Characters for a key", s)
            case DootTaskArtifact(path=path) | (pl.Path() as path) if not strict:
                return DootMultiKey(path)
            case str() if not (s_keys := PATTERN.findall(s)) and not explicit:
                return DootSimpleKey(s)
            case str() if len(s_keys) == 1 and s_keys[0] == s[1:-1]:
                # This means the is numeric check runs on the chopped key
                return DootKey.make(s[1:-1])
            case str() if not explicit:
                return DootMultiKey(s)
            case str():
                return DootNonKey(s)
            case pl.Path():
                return None
            case _:
                raise TypeError("Bad Type to build a Doot Key Out of", s)

    @property
    def form(self) -> str:
        return str(self)

    @property
    def is_indirect(self) -> bool:
        return False

    @property
    def redirect(self, spec, chain=None) -> DootKey:
        return self

    def to_path(self, spec=None, state=None, chain=None, locs=None) -> pl.Path:
        """
          Convert a key to an absolute path
        """
        locs                 = locs or doot.locs
        key                  = pl.Path(self.form)

        try:
            expanded             = [DootFormatter.fmt().format(x, _spec=spec, _state=state, _rec=True) for x in key.parts]
            expanded_as_path     = pl.Path().joinpath(*expanded)
            depth = 0
            while PATTERN.search(str(expanded_as_path)) and depth < MAX_KEY_EXPANSIONS:
                to_keys             = [DootKey.make(x, explicit=True) or x for x in expanded_as_path.parts]
                loc_expansions      = [locs.get(x) for x in to_keys]
                expanded_as_path    = pl.Path().joinpath(*loc_expansions)
                depth += 1

            if any(bool(matches) for x in expanded_as_path.parts if (matches:=PATTERN.findall(x))):
                raise doot.errors.DootLocationExpansionError("Missing keys on path expansion", matches)

            return locs.expand(expanded_as_path)

        except doot.errors.DootLocationExpansionError as err:
            if chain is None:
                raise err
            return chain.to_path(spec, state)

    def within(self, other:str|dict|TomlGuard) -> bool:
        return False

    @abc.abstractmethod
    def to_type(self, spec, state, type_=Any, chain:DootKey=None) -> Any:
        raise NotImplementedError()

    @abc.abstractmethod
    def expand(self, spec=None, state=None, *, rec=False) -> str:
        pass

class DootNonKey(str, DootKey):
    """
      Just a string, not a key. But this lets you call no-ops for key specific methods
    """

    def __repr__(self):
        return "<DootNonKey: {}>".format(str(self))

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        match other:
            case DootKey() | str():
                return str(self) == str(other)
            case _:
                return False

    def within(self, other:str|dict|TomlGuard) -> bool:
        match other:
            case str():
                return self.form in other
            case dict() | TomlGuard():
                return self in other
            case _:
                raise TypeError("Uknown DootKey target for within", other)

    @property
    def indirect(self) -> DootKey:
        if not self.is_indirect:
            return DootSimpleKey("{}_".format(super().__str__()))
        return self

    @property
    def is_indirect(self):
        return False

    @property
    def form(self):
        """ Return the key in its use form """
        return str(self)

    def expand(self, spec=None, state=None, *, rec=False) -> str:
        return str(self)

    def redirect(self, spec=None, chain=None) -> DootKey:
        return self

    def to_type(self, spec, state, type_=Any, chain:DootKey=None) -> Any:
        if type_ != Any or type_ != str:
            raise TypeError("NonKey's can only be strings")
        return str(self)

class DootSimpleKey(str, DootKey):
    """
      A Single key with no extras.
      ie: {x}. not {x}{y}, or {x}.blah.
    """

    def __repr__(self):
        return "<DootSimpleKey: {}>".format(str(self))

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        match other:
            case DootKey() | str():
                return str(self) == str(other)
            case _:
                return False

    def within(self, other:str|dict|TomlGuard) -> bool:
        match other:
            case str():
                return self.form in other
            case dict() | TomlGuard():
                return self in other
            case _:
                raise TypeError("Uknown DootKey target for within", other)

    @property
    def indirect(self):
        if not self.is_indirect:
            return DootSimpleKey("{}_".format(super().__str__()))
        return self

    @property
    def is_indirect(self):
        return str(self).endswith("_")

    @property
    def form(self):
        """ Return the key in its use form """
        return "{{{}}}".format(str(self))

    def expand(self, spec=None, state=None, *, rec=False) -> str:
        key = self.redirect(spec)
        fmt = DootFormatter()
        return fmt.format(key, _spec=spec, _state=state, _rec=rec)

    def redirect(self, spec=None, chain=None) -> DootKey:
        """
          If the indirect form of the key is found in the spec, use that instead
        """
        if not spec:
            return self

        match spec.kwargs.get(self.indirect, self):
            case str() as x if x == self.indirect:
                return self
            case str() as x:
                return DootKey.make(x)
            case list() as lst:
                raise TypeError("Key Redirectio resulted in a list, use redirect_multi", self)
            case _ if chain:
                return chain

        return self

    def redirect_multi(self, spec=None) -> list[DootKey]:
        if not spec:
            return [self]

        match spec.kwargs.get(self.indirect, self):
            case str() as x if x == self:
                return [self]
            case str() as x:
                return [DootKey.make(x)]
            case list() as lst:
                return [DootKey.make(x) for x in lst]

        return [self]

    def to_type(self, spec, state, type_=Any, chain:DootKey=None) -> Any:
        target            = self.redirect(spec)
        kwargs            = spec.kwargs
        cli               = doot.args.on_fail({}).tasks[str(state.get('_task_name', None))]()
        replacement       = cli.get(target, None)
        if replacement is None:
            replacement = state.get(target, None)
        if replacement is None:
            replacement = kwargs.get(target, None)

        match replacement:
            case None if chain:
                return chain.to_type(spec, state, type_=type)
            case None if type_ is Any or type_ is None:
                return None
            case _ if type_ is Any:
                return replacement
            case _ if type_ and isinstance(replacement, type_):
                return replacement
            case _:
                raise TypeError("Unexpected Type for replacement", type, replacement, self)

class DootMultiKey(DootKey):
    """ A string or path of multiple keys """

    def __init__(self, val:str|pl.Path):
        self.value : str|pl.Path        = val
        self._keys : set[DootSimpleKey] = set(DootSimpleKey(x) for x in PATTERN.findall(str(val)))

    def __str__(self):
        return str(self.value)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        match other:
            case DootKey() | str() | pl.Path():
                return str(self) == str(other)
            case _:
                return False

    def keys(self) -> set(DootSimpleKey):
        return self._keys

    @property
    def form(self):
        """ Return the key in its use form """
        return str(self)

    def expand(self, spec=None, state=None, *, rec=False):
        fmt = DootFormatter()
        return fmt.format(self.value, _spec=spec, _state=state, _rec=rec)

    def within(self, other:str|dict|TomlGuard) -> bool:
        return str(self) in other

    def to_type(self, spec, state, type_=Any, chain:DootKey=None) -> Any:
        raise TypeError("Converting a MultiKey to a type doesn't make sense", self)

class DootKeyChain(DootKey):
    pass
