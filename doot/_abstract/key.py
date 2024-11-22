#!/usr/bin/env python3
"""


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

from jgdv.enums.util import EnumBuilder_m, FlagsBuilder_m

# ##-- 1st party imports
from doot._abstract.protocols import Key_p
# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

CONV_SEP        : Final[str]                = "!"
REDIRECT_SUFFIX : Final[str]                = "_"

class DKeyMark_e(EnumBuilder_m, enum.Enum):
    """
      Enums for how to use/build a dkey

    """
    FREE     = enum.auto() # -> Any
    PATH     = enum.auto() # -> pl.Path
    REDIRECT = enum.auto() # -> DKey
    STR      = enum.auto() # -> str
    CODE     = enum.auto() # -> coderef
    TASK     = enum.auto() # -> taskname
    ARGS     = enum.auto() # -> list
    KWARGS   = enum.auto() # -> dict
    POSTBOX  = enum.auto() # -> list
    NULL     = enum.auto() # -> None
    MULTI    = enum.auto()

    default  = FREE
class DKeyMeta(type(str)):
    """
      The Metaclass for keys, which ensures that subclasses of DKeyBase
      are DKey's, despite there not being an actual subclass relation between them
    """

    def __call__(cls, *args, **kwargs):
        """ Runs on class instance creation
        skips running cls.__init__, allowing cls.__new__ control
        """
        # TODO maybe move dkey discrimination to here
        return cls.__new__(cls, *args, **kwargs)

    def __instancecheck__(cls, instance):
        return any(x.__instancecheck__(instance) for x in {Key_p})

    def __subclasscheck__(cls, sub):
        candidates = {Key_p}
        return any(x in candidates for x in sub.mro())

class DKey(metaclass=DKeyMeta):
    """ A facade for DKeys and variants.
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
    mark                                   = DKeyMark_e
    _single_registry : dict[DKeyMark_e,type] = {}
    _multi_registry  : dict[DKeyMark_e,type] = {}
    _conv_registry   : dict[str, DKeyMark_e] = {}
    _parser          : None|type           = None

    def __new__(cls, data:str|DKey|pl.Path|dict, *, fmt=None, conv=None, implicit=False, mark:None|DKeyMark_e=None, **kwargs) -> DKey:
        """
          fmt : Format parameters. used from multi key subkey construction
          conv : Conversion parameters. used from multi key subkey construction.
          implicit: For marking a key as an implicit key, with no extra text around it
          mark     : Enum for explicitly setting the key type
        """
        assert(cls is DKey)
        assert(isinstance(mark, None|DKeyMark_e)), mark
        # Early escape check
        match data:
            case DKey() if mark is None or mark == data._mark:
                return data
            case DKey() | pl.Path():
                data = str(data)
            case _:
                pass

        fparams = fmt or ""
        # Extract subkeys
        has_text, s_keys = DKey._parser.Parse(data)
        use_multi_ctor   = len(s_keys) > 0
        match len(s_keys):
            case 0 if not implicit and mark is not DKey.mark.PATH:
                # Just Text,
                mark = DKeyMark_e.NULL
            case _ if mark is DKey.mark.MULTI:
                # Explicit override
                pass
            case 0:
                # Handle Single, implicit Key variants
                data, mark     = cls._parse_single_key_params_to_mark(data, conv, fallback=mark)
            case 1 if not has_text:
                # One Key, no other text, so make a solo key
                solo           = s_keys[0]
                fparams        = solo.format
                data, mark     = cls._parse_single_key_params_to_mark(solo.key, solo.conv, fallback=mark)
                use_multi_ctor = False
            case x if not has_text and s_keys[0].conv == "p":
                mark = DKeyMark_e.PATH
            case _ if implicit:
                raise ValueError("Implicit instruction for multikey", data)
            case _ if has_text and mark is None:
                mark = DKey._conv_registry.get(DKeyMark_e.MULTI)
            case x if x >= 1 and mark is None:
                mark = DKeyMark_e.MULTI

        # Get the initiator using the mark
        key_init = DKey.get_initiator(mark, multi=use_multi_ctor)

        # Build a str with the key_init and data
        result           = str.__new__(key_init, data)
        result.__init__(data, fmt=fparams, mark=mark, **kwargs)

        return result

    @classmethod
    def _parse_single_key_params_to_mark(cls, data, conv, fallback=None) -> tuple(str, None|DKeyMark_e):
        """ Handle single, implicit key's and their parameters.
          Explicitly passed in conv take precedence

          eg:
          blah -> FREE
          blah_ -> REDIRECT
          blah!p -> PATH
          ...
        """
        key = data
        if not conv and CONV_SEP in data:
            key, conv = data.split(CONV_SEP)

        assert(conv is None or len(conv ) < 2), conv
        result = DKey._conv_registry.get(conv, DKeyMark_e.FREE)

        match fallback, result:
            case _, _ if key.endswith(REDIRECT_SUFFIX):
                return key, DKeyMark_e.REDIRECT
            case None, x:
                return (key, x)
            case x, DKeyMark_e.FREE:
                return (key, x)
            case x, y if x == y:
                return (key, x)
            case x, y:
                raise ValueError("Conflicting conversion parameters", x, y, data)


    @staticmethod
    def register_key(ctor:type, mark:DKeyMark_e, tparam:None|str=None, multi=False):
        match mark:
            case None:
                pass
            case DKey.mark.NULL:
                DKey._multi_registry[mark] = ctor
                DKey._single_registry[mark] = ctor
            case _ if multi:
                DKey._multi_registry[mark] = ctor
            case _:
                DKey._single_registry[mark] = ctor

        match tparam:
            case None:
                return
            case str() if len(tparam) > 1:
                raise ValueError("conversion parameters for DKey's can't be more than a single char")
            case str():
                DKey._conv_registry[tparam] = mark

    @staticmethod
    def get_initiator(mark, *, multi:bool=False) -> type:
        match multi:
            case True:
                ctor = DKey._multi_registry.get(mark, None)
                return ctor or DKey._multi_registry[DKeyMark_e.MULTI]
            case False:
                ctor = DKey._single_registry.get(mark, None)
                return ctor or DKey._single_registry[DKeyMark_e.FREE]


    @staticmethod
    def register_parser(fn:type, *, force=False):
        """ Dependency inject a formatter capable of parsing type conversion and formatting parameters from strings,
          for DKey to use when constructing keys.
          Most likely will be DKeyFormatter.

          Expects the fn to return tuple[bool, list]
        """
        match DKey._parser:
            case None:
                DKey._parser = fn
            case _ if force:
                DKey._parser = fn
            case _:
                pass
