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
from doot.enums import DKeyMark_e
from doot._abstract.protocols import Key_p, SpecStruct_p
from doot._structs.code_ref import CodeReference
from doot.utils.decorators import DecorationUtils, DootDecorator

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
logging.disabled = True
##-- end logging


KEY_PATTERN                                = doot.constants.patterns.KEY_PATTERN
MAX_KEY_EXPANSIONS                         = 200 # doot.constants.patterns.MAX_KEY_EXPANSIONS
STATE_TASK_NAME_K                          = doot.constants.patterns.STATE_TASK_NAME_K

FMT_PATTERN    : Final[re.Pattern]         = re.compile("[wdi]+")
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

      and makes the formatter a context manager, to hold the current data sources
      """
    _instance     : ClassVar[Self]      = None

    sources       : list                = []
    fallback      : Any                 = None

    rec_remaining : int                 = MAX_KEY_EXPANSIONS

    _entered      : bool                = False
    _original_key : str | Key_p         = None

    @classmethod
    def Parse(cls, key:Key_p|pl.Path) -> list:
        """ Use the python c formatter parser to extract keys from a string
          of form (key, format, conversion)

          see: cpython Lib/string.py
          and: cpython Objects/stringlib/unicode_format.h
          """
        if not cls._instance:
            cls._instance = cls()

        match key:
            case None:
                return []
            case str() | Key_p():
                # formatter.parse returns tuples of (literal, key, format, conversion)
                result = [x[1:] for x in cls._instance.parse(key) if x[1] is not None]
                return result
            case _:
                raise TypeError("Unknown type found", key)

    @classmethod
    def TypeConv(cls, val:None|str) -> None|DKeyMark_e:
        """ convert a string of type conversions to a DKeyMark_e"""
        if not bool(val):
            return None
        if "p" in val: # PATH
            return DKeyMark_e.PATH
        if "R" in val: # Redirect
            return DKeyMark_e.REDIRECT
        if "m" in val and "r" in val: # multi redirect
            # kwargs['multi'] = True
            return DKeyMark_e.REDIRECT
        if "c" in val: # coderef
            return DKeyMark_e.CODE
        if "t" in val: # taskname
            return DKeyMark_e.TASK

        return None

    def __call__(self, *, key=None, sources=None, fallback=None, rec=None) -> Self:
        if self._entered:
            raise RuntimeError("trying to enter an already entered formatter")
        self._entered          = True
        self._original_key     = key
        self.sources           = sources
        self.fallback          = fallback
        self.rec_remaining     = rec or MAX_KEY_EXPANSIONS
        return self

    def __enter__(self) -> Any:
        logging.debug("Entering Expansion/Redirection for: %s", self._original_key)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        self._original_key = None
        self._entered      = False
        self.sources       = []
        self.fallback      = None
        self.rec_remaining = 0
        return

class DKeyFormatter_Expansion_m:

    _multikey_expansion_types = (str, pl.Path)

    @classmethod
    def expand(cls, key:Key_p, *, sources=None, max=None, **kwargs) -> None|Any:
        """ static method to a singleton key formatter """
        if not cls._instance:
            cls._instance = cls()

        fallback               = kwargs.get("fallback", None)
        with cls._instance(key=key, sources=sources, fallback=fallback, rec=max) as fmt:
            result = fmt._expand(key)
            logging.debug("Expansion Result: %s", result)
            return result

    @classmethod
    def redirect(cls, key:Key_p, *, sources=None, **kwargs) -> list[Key_p|str]:
        """ static method to a singleton key formatter """
        if not cls._instance:
            cls._instance = cls()

        fallback               = kwargs.get("fallback", None)
        with cls._instance(key=key, sources=sources, fallback=fallback, rec=1) as fmt:
            result = fmt._try_redirection(key)
            logging.debug("Redirection Result: %s", result)
            return result

    def _expand(self, key:Key_p|str, *, fallback=None, count=1) -> None|Any:
        last               = None
        current            = key

        while 0 < self.rec_remaining and last != current:
            logging.debug("Expansion Loop (%s): %s %s", self.rec_remaining, current, type(current))
            self.rec_remaining -= count
            last                = current
            match current:
                case Key_p() if current.multi:
                    current = self._multi_expand(current)
                case Key_p():
                    current = self._try_redirection(current)[0]
                    current = self._single_expand(current)
                case str():
                    current = self._try_redirection(current)[0]
                    current = self._str_expand(current) or current
                case _:
                    break

        match current:
            case None:
                return fallback or self.fallback
            case x if x is key:
                return fallback or self.fallback
            case _:
                return current

    def _try_redirection(self, key:str|Key_p) -> list[Key_p]:
        """ Try to redirect a key if necessary,
          if theres no redirection, return the key as a direct key
          """
        keystr = self.format_field(key, "i")
        match chained_get(keystr, *self.sources):
            case list() as ks:
                logging.debug("Redirected %s to %s", key, ks)
                return ks
            case Key_p() as k:
                logging.debug("Redirected %s to %s", key, k)
                return [k]
            case str() as k:
                logging.debug("Redirected %s to %s", key, k)
                return [k]
            case _:
                logging.debug("No Redirection found for %s", keystr)
                return [self.format_field(key, "d")]

    def _single_expand(self, key:Key_p) -> None|Any:
        """
          Expand a single key up to {rec_remaining} times
        """
        logging.debug("Single Expansion: %s", key)
        # list[(keystr, lift_result_to_key))
        expanded          = [key]
        key_str           = self.format_field(key, "d")
        # key_str, lift   = echain.pop()
        match chained_get(key_str, *self.sources):
            case None:
                return None
            case Key_p() as x:
                return x
            case x if x == key_str:
                # Got the key back, wrap it and maybe return it
                return key
            case x:
                return x

    def _multi_expand(self, key:Key_p) -> Any:
        """
        expand a multi key
        """
        logging.debug("Multi Expansion: %s", key)
        expansion_dict = { f"{x}" : str(self._expand(x, fallback=f"{x:w}", count=0)) for x in key.keys() }
        expanded       = self.format(key, **expansion_dict)

        return expanded

    def _str_expand(self, key:str, *, fallback=None) -> Any:
        """
          Expand a raw string as either an implicit key or explicit multikey, into the sources
        """
        logging.debug("Str Expansion: %s", key)
        match self.Parse(key):
            case []:
                # no {keys}, so treat it as am implicit single key
                # TODO handle redirection
                return chained_get(key, *self.sources)
            case [*xs]:
                # {keys}, so expand them
                prepped = [(x[0], self.format_field(x[0], "w")) for x in xs]
                expansion_dict = { x[0] : self._expand(x[0], fallback=x[1], count=0) for x in prepped}
                expanded = self.format(key, **expansion_dict)
                return expanded
            case _:
                return key

class DKeyFormatter(string.Formatter, DKeyFormatter_Expansion_m, DKeyFormatterEntry_m):
    """
      An Expander/Formatter to extend string formatting with options useful for dkey's
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
        fallback               = kwargs.get("fallback", None)

        with cls._instance(key=key, sources=[spec, state, locs], fallback=fallback) as fmt:
            return fmt.format(key, *args, **kwargs)

    def format(self, key:str|Key_p, /, *args, **kwargs) -> str:
        """ format keys as strings """
        match key:
            case Key_p():
                fmt = f"{key}"
            case str():
                keys = DKeyFormatter.Parse(key)
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
        logging.debug("Expanding: %s. Args: %s. kwargs: %s", key, args, kwargs)
        if isinstance(key, int):
            return args[key]

        return kwargs.get(key, key)

    def convert_field(self, value, conversion):
        # do any conversion on the resulting object
        match conversion:
            case None:
                return value
            case "s" | "p" | "R" | "c" | "t":
                return str(value)
            case "r":
                return repr(value)
            case "a":
                return ascii(value)

        raise ValueError("Unknown conversion specifier {0!s}".format(conversion))

    @staticmethod
    def format_field(val, spec):
        logging.debug("Formatting %s:%s", val, spec)
        match val:
            case Key_p():
                return format(val, spec)

        wrap     = 'w' in spec
        direct   = 'd' in spec or not "i"  in spec
        remaining = FMT_PATTERN.sub("", spec)

        result = str(val)
        if direct:
            result = result.removesuffix("_")
        elif not result.endswith("_"):
            result = f"{result}_"

        if wrap:
            result = "".join(["{", result, "}"])

        return format(result, remaining)
