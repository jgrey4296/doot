#!/usr/bin/env python3
"""

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
from jgdv.structs.code_ref import CodeReference
import sh

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.key import DKey
from doot.enums import DKeyMark_e
from doot._abstract.protocols import Key_p, SpecStruct_p
from doot.utils.decorators import DecorationUtils, DootDecorator

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__file__)
printer = doot.subprinter()
# logging = printer.getChild("expansion")
##-- end logging

KEY_PATTERN                                = doot.constants.patterns.KEY_PATTERN
MAX_KEY_EXPANSIONS                         = 200 # doot.constants.patterns.MAX_KEY_EXPANSIONS
STATE_TASK_NAME_K                          = doot.constants.patterns.STATE_TASK_NAME_K

FMT_PATTERN    : Final[re.Pattern]         = re.compile("[wdi]+")
PATTERN        : Final[re.Pattern]         = re.compile(KEY_PATTERN)
FAIL_PATTERN   : Final[re.Pattern]         = re.compile("[^a-zA-Z_{}/0-9-]")
EXPANSION_HINT : Final[str]                = "_doot_expansion_hint"
HELP_HINT      : Final[str]                = "_doot_help_hint"
MAX_DEPTH      : Final[int]                = 10


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
        with cls._instance(key=key, sources=sources, fallback=fallback, rec=max, intent="expand") as fmt:
            result = fmt._expand(key)
            logging.debug("Expansion Result: %s", result)
            return result

    @classmethod
    def redirect(cls, key:Key_p, *, sources=None, **kwargs) -> list[Key_p|str]:
        """ static method to a singleton key formatter """
        if not cls._instance:
            cls._instance = cls()

        match key:
            case DKey():
                pass
            case str():
                key = DKey(key)
        fallback               = kwargs.get("fallback", None)
        with cls._instance(key=key, sources=sources, fallback=fallback, rec=1, intent="redirect") as fmt:
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
        # locs                   = kwargs.get('locs', doot.locs)
        fallback               = kwargs.get("fallback", None)

        with cls._instance(key=key, sources=[spec, state], fallback=fallback, intent="format") as fmt:
            return fmt.format(key, *args, **kwargs)

    def __call__(self, *, key=None, sources=None, fallback=None, rec=None, intent=None, depth=None) -> Self:
        if self._entered:
            # Create a new temporary instance
            return self.__class__()(key=key or self._original_key,
                                    sources=sources or self.sources,
                                    fallback=fallback or self.fallback,
                                    intent=intent or self._intent,
                                    depth=depth or self._depth+1)
        self._entered          = True
        self._original_key     = key
        self.sources           = list(sources)
        self.fallback          = fallback
        self.rec_remaining     = rec or MAX_KEY_EXPANSIONS
        self._intent           = intent
        self._depth            = depth or 1
        return self

    def __enter__(self) -> Any:
        logging.debug("--> (%s) Context for: %s", self._intent, self._original_key)
        logging.debug("Using Sources: %s", self.sources)
        if self._depth > MAX_DEPTH:
            raise RecursionError("Hit Max Formatter Depth", self._depth)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        logging.debug("<-- (%s) Context for: %s", self._intent, self._original_key)
        self._original_key = None
        self._entered      = False
        self.sources       = []
        self.fallback      = None
        self.rec_remaining = 0
        self._intent       = None
        return

class DKeyFormatter_Expansion_m:

    def _expand(self, key:Key_p|str, *, fallback=None, count=1) -> None|Any:
        """
          Expand the key, returning fallback if it fails,
          counting each loop as `count` attempts

        """
        current : DKey
        last    : set[str] = set()
        match key:
            case Key_p():
                current = key
            case _:
                current = DKey(key)

        while 0 < self.rec_remaining and str(current) not in last:
            logging.debug("--- Loop (%s:%s) [%s] : %s", self._depth, MAX_KEY_EXPANSIONS - self.rec_remaining, key, repr(current))
            self.rec_remaining -= count
            last.add(str(current))
            match current:
                case sh.Command():
                    break
                case Key_p() if current._mark is DKey.mark.PATH and count != 2:
                    with self(sources=self.sources + current.extra_sources()) as sub:
                        logging.debug("Handling Path key")
                        current = sub._expand(current, count=2)
                case Key_p() if current.multi:
                    current = self._multi_expand(current)
                case Key_p():
                    redirected = self._try_redirection(current)[0]
                    current    = self._single_expand(redirected) or current
                case _:
                    break

        match current:
            case None:
                current = fallback or self.fallback
            case x if str(x) == str(key):
                current = fallback or self.fallback
            case _:
                pass

        if isinstance(key, Key_p) and current is not None:
            logging.debug("Running Expansion Hook: (%s) -> (%s)", key, current)
            exp_val = key._exp_type(current)
            key._check_expansion(exp_val)
            current = key._expansion_hook(exp_val)

        logging.debug("Expanded (%s) -> (%s)", key, current)
        return current

    def _multi_expand(self, key:Key_p) -> str:
        """
        expand a multi key,
          by formatting the anon key version using a sequenec of expanded subkeys,
          this allows for duplicate keys to be used differenly in a single multikey
        """
        logging.debug("multi(%s)", key)
        # expanded_keys   = [ str(self._expand(x, fallback=f"{x:w}", count=0)) for x in key.keys() ]
        logging.debug("----> %s", key.keys())
        expanded_keys   = [ str(self._expand(x, fallback=f"{x:w}", count=0)) for x in key.keys() ]
        expanded        = self.format(key._unnamed, *expanded_keys)
        logging.debug("<---- %s", key.keys())
        return DKey(expanded)

    def _try_redirection(self, key:Key_p) -> list[Key_p]:
        """ Try to redirect a key if necessary,
          if theres no redirection, return the key as a direct key
          """
        # key_str = self.format_field(key, "i")
        key_str = f"{key:i}"
        match chained_get(key_str, *self.sources, *key.extra_sources()):
            case list() as ks:
                logging.debug("(%s -> %s -> %s)", key, key_str, ks)
                return [DKey(x, implicit=True) for x in ks]
            case Key_p() as k:
                logging.debug("(%s -> %s -> %s)", key, key_str, k)
                return [k]
            case str() as k:
                logging.debug("(%s -> %s -> %s)", key, key_str, k)
                return [DKey(k, implicit=True)]
            case None:
                logging.debug("(%s -> %s -> Ø)", key, key_str)
                return [key]

    def _single_expand(self, key:Key_p, fallback=None) -> None|Any:
        """
          Expand a single key up to {rec_remaining} times
        """
        assert(isinstance(key, Key_p))
        logging.debug("solo(%s)", key)
        # key_str           = self.format_field(key, "d")
        key_str             = f"{key:d}"
        wrapped             = f"{key:w}"
        match chained_get(key_str, *self.sources, *key.extra_sources(), fallback=fallback):
            case None:
                return None
            case Key_p() as x:
                return x
            case str() as x if x == wrapped:
                return DKey(x, mark=DKey.mark.NULL)
            case str() as x if x == key_str:
                # Got the key back, wrap it and don't expand it any more
                return "{%s}" % key
            case str() as x:
                return DKey(x)
            case pl.Path() as x:
                return DKey(x, mark=DKey.mark.PATH)
            case x:
                return x

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
    def format_field(val, spec) -> str:
        """ Take a value and a formatting spec, and apply that formatting """
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
