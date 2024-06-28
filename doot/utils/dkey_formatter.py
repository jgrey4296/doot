#!/usr/bin/env python3
"""

key formatting:

- key.format()
- "{}".format(key)
- format(key, spec)

key -> str:
keep as a key if missing.
{x} -> {x}

_expand to string if not missing:
{x} -> blah
respect format specs if not missing:
{x: <5} -> 'blah  '
keep format specs if missing:
{x: <5} -> {x: <5}

-----

key expansion:
- key._expand(fmtspec, spec=actionspec, state=state)
- key(spec, state)

key -> str by default.

key -> path|type if conversion spec
{x!t} -> dict() etc..

----

format(DKey, fmt) -> DKey.__format__ -> str
DKey.__format__   -> str
Dkey.format       -> DKeyFormatter.fmt -> KF._expand -> KF.format -> str
DKey._expand       -> KF._expand -> KF.format -> KF._expand -> Any

----

Extends the format string syntax
https://docs.python.org/3/library/string.html#format-string-syntax
with additional DKey options:

Type Conversion:
!t : type formatting  eg: '{x!t}'+{x:dict(a=2,b=3)}    -> 'dict(a=2,b=3)'
!_ : key redirection. eg: '{x!_}'+{x_:blah, blah:bloo} -> {blah}
!k : as key,          eg: '{x!k}'+{x:blah, blah:bloo}  -> '{bloo}'
!CR : as coderef      eg: '{x!cr}'+{x:'doot.utils.key_formatter:DKeyFormatter} -> DKeyFormatter

and formating controls:

:.[0-9] : using precision for amount of recursive expansion
:#      : using alt form for 'direct' key: {key}
:#_     : indirect key form: {key_}
:...!   : bang at end of format spec means insist on expansion

Used for DootKey.__format__
format(DootKey, spec)
DootKey._expand
and '{spec}'.format(DootKey)

Keys can have a number of forms:
{x}  : Direct Expansion form
{x_} : Indirect Expansion form
x    : Name form, no expansion

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
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
from doot.utils.decorators import DecorationUtils, DootDecorator

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

KEY_PATTERN                                = doot.constants.patterns.KEY_PATTERN
MAX_KEY_EXPANSIONS                         = doot.constants.patterns.MAX_KEY_EXPANSIONS
STATE_TASK_NAME_K                          = doot.constants.patterns.STATE_TASK_NAME_K

PATTERN        : Final[re.Pattern]         = re.compile(KEY_PATTERN)
FAIL_PATTERN   : Final[re.Pattern]         = re.compile("[^a-zA-Z_{}/0-9-]")
EXPANSION_HINT : Final[str]                = "_doot_expansion_hint"
HELP_HINT      : Final[str]                = "_doot_help_hint"

def chained_get(key:Key_p, *sources:dict|SpecStruct_p|DootLocations) -> None|Any:
    """
      Get a key's value from an ordered sequence of potential sources.
      Try to get {key} then {key_} in order of sources passed in
    """
    replacement = None
    for source in sources:
        match source:
            case None:
                continue
            case _ if hasattr(source, "get"):
                replacement = source.get(key, None)
            case SpecStruct_p():
                params      = source.params
                replacement = params.get(key, None)

        if replacement is not None:
            return replacement

    return None

class DKeyFormatterEntry_m:
    """ Mixin to make DKeyFormatter a singleton with static access
      via 'fmt' and 'exp', for formatting and expansion

      and makes the formatter a context manager, to hold the current state and spec
      """
    _instance     : ClassVar[Self]      = None

    sources       : list                = []
    fallback      : Any                 = None

    rec_remaining : int                 = MAX_KEY_EXPANSIONS

    @classmethod
    def Parse(cls, key:Key_p|pl.Path) -> list:
        """ Use the python c formatter parser to extract keys from a string
          of form (literal, key, format, conversion)

          see: cpython Lib/string.py
          and: cpython Objects/stringlib/unicode_format.h
          """
        if not cls._instance:
            cls._instance = cls()

        match key:
            case None:
                return []
            case str() | Key_p():
                result = [x[1:] for x in cls._instance.parse(key) if x[1] is not None]
                return result
            case _:
                raise TypeError("Unknown type found", key)

    def __call__(self, *, sources=None, fallback=None, rec=None) -> Self:
        self.sources       = sources
        self.fallback      = fallback
        if self.rec_remaining == 0:
            self.rec_remaining = rec or MAX_KEY_EXPANSIONS
        return self

    def __enter__(self) -> Any:
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        self.sources = []
        self.fallback      = None
        self.rec_remaining = 0
        return

class DKeyFormatter_Expansion_m:

    @classmethod
    def expand(cls, key:Key_p|pl.Path, *, sources=None, **kwargs) -> None|Any:
        """ static method to a singleton key formatter """
        if not cls._instance:
            cls._instance = cls()

        fallback               = kwargs.get("on_fail", None)
        with cls._instance(sources=sources, fallback=fallback) as fmt:
            return fmt._expand(key)


    @classmethod
    def redirect(cls, key:Key_p|pl.Path, *, sources=None, **kwargs) -> None|Any:
        """ static method to a singleton key formatter """
        if not cls._instance:
            cls._instance = cls()

        fallback               = kwargs.get("on_fail", None)
        with cls._instance(sources=sources, fallback=fallback) as fmt:
             return fmt._expand(key, depth=1)


    def _expand(self, key:Key_p|str|pl.Path, *, depth:int=MAX_KEY_EXPANSIONS, on_fail=None) -> None|Any:
        result = None
        if depth <= 0:
            logging.debug("No more expansions allowed: %s", key)
            return key

        match key:
            case Key_p() if bool(key.keys()):
                result = self._multi_expand(key, depth=depth)
            case Key_p():
                result = self._single_expand(key, depth=depth)
            case str():
                result = self._str_expand(key, depth=depth)
            case _:
                raise TypeError("Unknown expansion entry type", key)

        match result:
            case None:
                return on_fail or self.fallback
            case _:
                return result

    def _str_expand(self, key:str, *, depth:int=MAX_KEY_EXPANSIONS, on_fail=None) -> None|Any:
        """

        """
        match self.Parse(key):
            case []:
                return chained_get(key, *self.sources)
            case [*xs]:
                expansion_dict = { f"{x:d}" : self._expand(x, on_fail=f"{x:w}", depth=depth-1) for x in xs }
                expanded = key.format_map(expansion_dict)
                return expanded

    def _single_expand(self, key:Key_p|str|pl.Path, *, depth:int=MAX_KEY_EXPANSIONS) -> None|Any:
        """
        """
        remaining_depth   = depth
        # list[(keystr, lift_result_to_key))
        echain            = [(f"{key:d}", False), (f"{key:i}", True)]
        expanded          = [None]

        if remaining_depth <= 0:
            logging.debug("No more expansions allowed: %s", key)
            return key

        for i in range(remaining_depth):
            if not bool(echain):
                break

            key_str, lift = echain.pop()
            match chained_get(key_str, *self.sources):
                case x if x == key_str:
                    expanded.append(f"{{{x}}}")
                case None:
                    continue
                case Key_p() as k:
                    mexp = self._expand(k, depth=depth-1)
                    expanded.append(mexp)
                    echain.append((mexp, lift))
                case str() as exp if lift:
                    expanded.append(exp)
                    echain.append((exp, lift))
                case x:
                    expanded.append(x)

        return expanded[-1]

    def _multi_expand(self, key:Key_p|str|pl.Path, *, depth:int=MAX_KEY_EXPANSIONS) -> None|Any:
        remaining_depth = depth
        if remaining_depth <= 0:
            logging.debug("No More Expansions allowed: %s", key)
            return key

        expansion_dict = { f"{x:d}" : self._expand(x, on_fail=f"{x:w}", depth=depth-1) for x in key.keys() }
        expanded = key.format_map(expansion_dict)
        return expanded


class DKeyFormatter_ExpansionPlus_m:
    def _to_penultimate_expansion(self, key, spec=None, state=None, limit=None) -> str:
        """ Find the final expansion, and use the one before it"""
        raise NotImplementedError()

    def _to_type(self, spec:None|SpecStruct_p=None, state=None, type_=Any, on_fail=Any) -> Any:
        target            = self._to_redirection(spec)

        match spec:
            case _ if hasattr(spec, "params"):
                kwargs = spec.params
            case None:
                kwargs = {}

        task_name = state.get(STATE_TASK_NAME_K, None) if state else None
        match (replacement:=chained_get(target[0], kwargs, state)):
            case None if on_fail != Any and isinstance(on_fail, DootKey):
                return on_fail._to_type(spec, state, type_=type_)
            case None if on_fail != Any:
                return on_fail
            case None if type_ is Any or type_ is None:
                return None
            case _ if type_ is Any:
                return replacement
            case _ if type_ and isinstance(replacement, type_):
                return replacement
            case None if not any(target in x for x in [kwargs, state]):
                raise KeyError("Key is not available in the state or spec", target)
            case _:
                raise TypeError("Unexpected Type for replacement", type_, replacement, self)

    def _to_path(self, spec=None, state=None, *, locs:DootLocations=None, on_fail:None|str|pl.Path|DootKey=Any, symlinks=False) -> pl.Path:
        """
          Convert a key to an absolute path, using registered locations

          The Process is:
          1) redirect the given key if necessary
          2) Expand each part of the keypath, using DKeyFormatter
          3) normalize it

          If necessary, a fallback chain, and on_fail value can be provided
        """
        locs                 = locs or doot.locs
        key : pl.Path        = pl.Path(self.redirect(spec).form)

        try:
            expanded         : list       = [DKeyFormatter.fmt(x, _spec=spec, _state=state, _rec=True, _locs=locs) for x in key.parts]
            expanded_as_path : pl.Path    = pl.Path().joinpath(*expanded) # allows ("a", "b/c") -> "a/b/c"

            if bool(matches:=PATTERN.findall(str(expanded_as_path))):
                raise doot.errors.DootLocationExpansionError("Missing keys on path expansion", matches, self)

            return locs.normalize(expanded_as_path, symlinks=symlinks)

        except doot.errors.DootLocationExpansionError as err:
            match on_fail:
                case None:
                    return None
                case DootKey():
                    return on_fail._to_path(spec, state, symlinks=symlinks)
                case pl.Path() | str():
                    return locs.normalize(pl.Path(on_fail),  symlinks=symlinks)
                case _:
                    raise err

    def _to_coderef(self, spec:None|SpecStruct_p, state) -> None|CodeReference:
        match spec:
            case _ if hasattr(spec, "params"):
                kwargs = spec.params
            case None:
                kwargs = {}

        redir = self.redirect(spec)

        if redir not in kwargs and redir not in state:
            return None
        try:
            expanded = self._expand(spec, state)
            ref = CodeReference.build(expanded)
            return ref
        except doot.errors.DootError:
            return None

    def _to_expansion_form(self, key):
        """ Return the key in its use form, ie: wrapped in braces """
        return "{{{}}}".format(str(key))

    def _to_redirection(self, key, fmt, spec:None|SpecStruct_p=None) -> list[str]:
        """
          If the indirect form of the key is found in the spec, use that as a key instead
        """
        if not spec:
            return self

        match spec:
            case _ if hasattr(spec, "params"):
                kwargs = spec.params
            case _:
                kwargs = {}

        match kwargs.get(self.indirect, self):
            case str() as x if x == self.indirect:
                return self
            case str() as x:
                return DootKey.build(x)
            case list() as lst:
                raise TypeError("Key Redirection resulted in a list, use redirect_multi", self)

        return self

    def to_multi_redirection(self, spec:None|SpecStruct_p=None) -> list[str]:
        """ redirect an indirect key to a *list* of keys """
        raise DeprecationWarning()
        if not spec:
            return [self]

        match spec:
            case _ if hasattr(spec, "params"):
                kwargs = spec.params
            case None:
                kwargs = {}

        match kwargs.get(self.indirect, self):
            case str() as x if x == self:
                return [self]
            case str() as x:
                return [DootKey.build(x)]
            case list() as lst:
                return [DootKey.build(x) for x in lst]

        return [self]

    def _parse_fmt_spec(self, fmt) -> dict:
        pass

class DKeyFormatter(string.Formatter, DKeyFormatter_Expansion_m, DKeyFormatterEntry_m):
    """
      A Formatter to extend string formatting with options useful for dkey's
      and doot specs/state.

    """

    @classmethod
    def fmt(cls, key:Key_p|str, /, *args, **kwargs) -> str:
        """ static method to a singleton key formatter """
        if not cls._instance:
            cls._instance = cls()

        spec                   = kwargs.get('spec', None)
        state                  = kwargs.get('state', None)
        locs                   = kwargs.get('locs', doot.locs)
        fallback               = kwargs.get("on_fail", None)

        with cls._instance(spec=spec, state=state, locs=locs, fallback=fallback) as fmt:
            return fmt.format(key, *args, **kwargs)

    def format(self, key:str|Key_p, /, *args, **kwargs) -> str:
        """ format keys as strings """
        match key:
            case Key_p():
                fmt = f"{key}"
            case str():
                fmt = key
            case pl.Path():
                # result = str(ftz.reduce(pl.Path.joinpath, [self.vformat(x, args, kwargs) for x in fmt.parts], pl.Path()))
                raise NotImplementedError()
            case _:
                raise TypeError("Unrecognized expansion type", fmt)

        result = self.vformat(fmt, args, kwargs)
        return result

    def get_value(self, key, args, kwargs) -> str:
        """ lowest level handling of keys being expanded """
        logging.debug("Expanding: %s", key)
        if isinstance(key, int):
            return args[key]

        insist                = kwargs.get("insist", False)
        depth_check           = self._depth < MAX_KEY_EXPANSIONS
        rec_allowed           = kwargs.get("rec", False) and depth_check

        match (replacement:=chained_get(key, *self.sources)):
            case None if insist:
                raise KeyError("Key Expansion Not Found")
            case None:
                # return DootKey.build(key).form
                return "{{{}}}".format(key)
            case Key_p() if depth_check:
                self._depth += 1
                return self.vformat(replacement.form, args, kwargs)
            case str() if rec_allowed:
                self._depth += 1
                return self.vformat(str(replacement), args, kwargs)
            case str():
                return replacement
            case pl.Path() if depth_check:
                self._depth += 1
                return ftz.reduce(pl.Path.joinpath, map(lambda x: self.vformat(x, args, kwargs), replacement.parts), pl.Path())
            case _:
                return str(replacement)
                # raise TypeError("Replacement Value isn't a string", args, kwargs)

    def convert_field(self, value, conversion):
        # do any conversion on the resulting object
        match conversion:
            case None:
                return value
            case "s":
                return str(value)
            case "r":
                return repr(value)
            case "a":
                return ascii(value)
            case "e": # e for _expand
                return self._expand(value)

        raise ValueError("Unknown conversion specifier {0!s}".format(conversion))
