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
logging.disabled = False
##-- end logging

KEY_PATTERN                                = doot.constants.patterns.KEY_PATTERN
MAX_KEY_EXPANSIONS                         = 200 # doot.constants.patterns.MAX_KEY_EXPANSIONS
STATE_TASK_NAME_K                          = doot.constants.patterns.STATE_TASK_NAME_K

FMT_PATTERN    : Final[re.Pattern]         = re.compile("[wdi]+")
PATTERN        : Final[re.Pattern]         = re.compile(KEY_PATTERN)
FAIL_PATTERN   : Final[re.Pattern]         = re.compile("[^a-zA-Z_{}/0-9-]")
EXPANSION_HINT : Final[str]                = "_doot_expansion_hint"
HELP_HINT      : Final[str]                = "_doot_help_hint"

def chained_get(key:Key_p, *sources:dict|SpecStruct_p|DootLocations, fallback=None) -> None|Any:
    """
      Get a key's value from an ordered sequence of potential sources.
      Try to get {key} then {key_} in order of sources passed in
    """
    replacement = fallback
    for source in sources:
        match source:
            case None | []:
                continue
            case list():
                replacement = source.pop()
            case _ if hasattr(source, "get"):
                if key not in source:
                    continue
                replacement = source.get(key, fallback)
            case SpecStruct_p():
                params      = source.params
                replacement = params.get(key, fallback)

        if replacement is not fallback:
            return replacement

    return fallback

class _DKeyParams(BaseModel):
    """ Utility class for parsed string parameters """

    prefix : None|str = ""
    key    : None|str = ""
    format : None|str = ""
    conv   : None|str = ""

    def __getitem__(self, i):
        match i:
            case 0:
                return self.prefix
            case 1:
                return self.key
            case 2:
                return self.format
            case 3:
                return self.conv

    def __bool__(self):
        return bool(self.key)

    def wrapped(self) -> str:
        return "{%s}" % self.key

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
    def Parse(cls, key:Key_p|pl.Path) -> tuple(bool, list[_DKeyParams]):
        """ Use the python c formatter parser to extract keys from a string
          of form (prefix, key, format, conversion)

          Returns: (bool: non-key text), list[(key, format, conv)]

          see: cpython Lib/string.py
          and: cpython Objects/stringlib/unicode_format.h

          eg: '{test:w} :: {blah}' -> False, [('test', Any, Any), ('blah', Any, Any)]
          """
        if not cls._instance:
            cls._instance = cls()

        try:
            match key:
                case None:
                    return True, []
                case str() | Key_p():
                    # formatter.parse returns tuples of (literal, key, format, conversion)
                    result = list(_DKeyParams(prefix=x[0], key=x[1] or "", format=x[2] or "", conv=x[3] or "") for x in cls._instance.parse(key))
                    non_key_text = any(bool(x.prefix) for x in result)
                    return non_key_text, [x for x in result if bool(x)]
                case _:
                    raise TypeError("Unknown type found", key)
        except ValueError:
            return True, []

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
        logging.debug("Using Sources: %s", self.sources)
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

    def _expand(self, key:Key_p|str, *, fallback=None, count=1) -> None|Any:
        logging.debug("Entering Formatter for: %s", key)
        last               = None
        current            = key

        while 0 < self.rec_remaining and last != current:
            logging.debug("-- Expansion Loop (%s): %s %s", self.rec_remaining, current, type(current))
            self.rec_remaining -= count
            last                = current
            match current:
                case Key_p() if current.multi and count > 0:
                    current = self._multi_expand(current)
                case Key_p():
                    current = self._try_redirection(current)[0]
                    current = self._single_expand(current)
                case str():
                    redirected = self._try_redirection(current)[0]
                    current = self._str_expand(redirected) or current
                case _:
                    break

        match current:
            case None:
                current = fallback or self.fallback
            case x if x is key:
                current = fallback or self.fallback
            case _:
                pass

        if isinstance(key, Key_p) and current is not None:
            exp_val = key._exp_type(current)
            key._check_expansion(exp_val)
            current = key._expansion_hook(exp_val)

        logging.debug("Expanded (%s) -> (%s)", key, current)
        return current

    def _multi_expand(self, key:Key_p) -> Any:
        """
        expand a multi key,
          by formatting the anon key version using a sequenec of expanded subkeys,
          this allows for duplicate keys to be used differenly in a single multikey
        """
        logging.debug("Multi Expansion: %s", key)
        expanded_keys   = [ str(self._expand(x, fallback=f"{x:w}", count=0)) for x in key.keys() ]
        expanded        = self.format(key._unnamed, *expanded_keys)
        return expanded

    def _try_redirection(self, key:Key_p) -> list[Key_p|str]:
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

    def _single_expand(self, key:str|Key_p, fallback=None) -> None|Any:
        """
          Expand a single key up to {rec_remaining} times
        """
        logging.debug("Single Expansion: %s", key)
        key_str           = self.format_field(key, "d")
        match chained_get(key_str, *self.sources, fallback=fallback):
            case None:
                return None
            case Key_p() as x:
                return x
            case x if x == key_str:
                # Got the key back, wrap it and maybe return it
                return "{%s}" % key
            case x:
                return x

    def _str_expand(self, key:str, *, fallback=None) -> Any:
        """
          Expand a raw string as either an implicit key or explicit multikey, into the sources
        """
        logging.debug("Str Expansion: %s", key)
        match self.Parse(key):
            case True, []:
                # no {keys}, so return the original key
                return key
            case _, [*xs]:
                # {keys}, so expand them
                anon           = self.format(key, **{x.key : "{}" for x in xs})
                expansion_list = [ self._single_expand(x[1], fallback=x[1]) for x in xs]
                expanded       = self.format(anon, *expansion_list)
                return expanded
            case _:
                return key

class DKeyFormatter(string.Formatter, DKeyFormatter_Expansion_m, DKeyFormatterEntry_m):
    """
      An Expander/Formatter to extend string formatting with options useful for dkey's
      and doot specs/state.

    """

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
        # logging.debug("Expanding: %s. Args: %s. kwargs: %s", key, args, kwargs)
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
        # logging.debug("Formatting %s:%s", val, spec)
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
            # result = "".join(["{", result, "}"])
            result = "{%s}" % result

        return format(result, remaining)
