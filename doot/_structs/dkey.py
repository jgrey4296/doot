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
from doot.utils.decorators import DecorationUtils, DootDecorator
from doot.utils.dkey_formatter import DKeyFormatter

# ##-- end 1st party imports

##-- type checking
if TYPE_CHECKING:
    DootLocations:TypeAlias = Any
##-- end type checking

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

KEY_PATTERN                                 = doot.constants.patterns.KEY_PATTERN
MAX_KEY_EXPANSIONS                          = doot.constants.patterns.MAX_KEY_EXPANSIONS
STATE_TASK_NAME_K                           = doot.constants.patterns.STATE_TASK_NAME_K

PATTERN         : Final[re.Pattern]         = re.compile(KEY_PATTERN)
FAIL_PATTERN    : Final[re.Pattern]         = re.compile("[^a-zA-Z_{}/0-9-]")
FMT_PATTERN     : Final[re.Pattern]         = re.compile("[wdi]+")
EXPANSION_HINT  : Final[str]                = "_doot_expansion_hint"
HELP_HINT       : Final[str]                = "_doot_help_hint"
REDIRECT_SUFFIX : Final[str]                = "_"
FORMAT_SEP      : Final[str]                = ":"
CONV_SEP        : Final[str]                = "!"
CHECKTYPE       : TypeAlias                 = None|type|types.GenericAlias|types.UnionType
MARKTYPE        : TypeAlias                 = None|DKeyMark_e|type

def identity(x):
    return x

##-- meta

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
        return any(x.__instancecheck__(instance) for x in {DKeyBase})

    def __subclasscheck__(cls, sub):
        candidates = {DKeyBase}
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
    _single_registry : dict[MARKTYPE,type] = {}
    _multi_registry  : dict[MARKTYPE,type] = {}
    _conv_registry   : dict[str, MARKTYPE] = {}

    def __new__(cls, data:str|DKey|pl.Path|dict, *, fparams=None, cparams=None, implicit=False, mark:None|MARKTYPE=None, **kwargs) -> DKey:
        """
          fparams  : Format parameters. used from multi key subkey construction
          cparams  : Conversion parameters. used from multi key subkey construction.
          explicit : For marking a key as using explicit subkeys with extra text around it
          mark     : Enum for explicitly setting the key type
        """
        assert(cls is DKey)
        assert(isinstance(mark, DKeyMark_e | None)), mark

        # Early escape
        match data:
            case DKey() if mark is None or mark == data._mark:
                return data
            case DKey() | pl.Path():
                data = str(data)
            case _:
                pass

        fparams = fparams or ""
        # Extract subkeys
        has_text, s_keys = DKeyFormatter.Parse(data)
        match len(s_keys):
            case _ if mark is not None:
                # explicit mark already provided
                pass
            case 0 if implicit:
                # Handle Single, implicit Key variants
                data, mark  = cls._parse_single_key_params_to_mark(data, cparams)
            case 0:
                mark = DKeyMark_e.NULL
            case x:
                if implicit:
                    logging.warning("Ignoring Implicit instruction for multikey: %s", data)
                assert(x > 0), x
                assert(not bool(cparams))
                # Handle Multi Key variants
                # Use the first explicit key to determine main conversion
                mark = DKey._conv_registry.get(s_keys[0].conv, DKeyMark_e.MULTI)

        # Get the ctor from the mark
        key_ctor = DKey.get_ctor(mark, multi=len(s_keys) > 0)

        # Build the key from key_ctor + init it
        result           = str.__new__(key_ctor, data)
        result.__init__(data, fparams=fparams, mark=mark, **kwargs)

        return result

    @classmethod
    def _parse_single_key_params_to_mark(cls, data, cparam) -> tuple(str, MARKTYPE):
        """ Handle single, non-explicit key's and their parameters.
          Explicitly passed in cparams take precedence

          eg:
          blah -> FREE
          blah_ -> REDIRECT
          blah!p -> PATH
          ...
        """
        key = data
        if not cparam and CONV_SEP in data:
            key, cparam = data.split(CONV_SEP)

        if key.endswith(REDIRECT_SUFFIX):
            return key, DKeyMark_e.REDIRECT

        assert(cparam is None or len(cparam) < 2), cparam
        return key, DKey._conv_registry.get(cparam, DKeyMark_e.FREE)

    @staticmethod
    def register_key(ctor:type, mark:MARKTYPE, tparam:None|str=None, multi=False):
        match mark:
            case None:
                pass
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
    def get_ctor(mark, *, multi:bool=False):
        match multi:
            case True:
                return DKey._multi_registry.get(mark, MultiDKey)
            case False:
                return DKey._single_registry.get(mark, SingleDKey)

##-- end meta

##-- expansion and formatting

class DKeyFormatting_m:

    """ General formatting for dkeys """

    def format(self, fmt, *, spec=None, state=None) -> str:
        return DKeyFormatter.fmt(self, fmt, **(state or {}))

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

    def set_fparams(self, params:str) -> Self:
        match params:
            case None:
                pass
            case str() if bool(params):
                self._fparams = params
        return self

class DKeyExpansion_m:
    """ general expansion for dkeys """

    def redirect(self, *sources, multi=False, re_mark=None) -> list[DKey]:
        """
          Always returns a list of keys, even if the key is itself
        """
        match DKeyFormatter.redirect(self, sources=sources):
            case []:
                return [DKey(f"{self:d}", mark=re_mark)]
            case [*xs] if multi:
                return [DKey(x, mark=re_mark, implicit=True) for x in xs]
            case [x]:
                return [DKey(x, mark=re_mark, implicit=True)]
            case x:
                raise TypeError("bad redirection type", x, self)

    def expand(self, *sources, fallback=None, max=None, check=None, **kwargs) -> None|Any:
        logging.debug("Entering expansion for: %s", self)
        # expanded_keys = {x : x.expand(*sources) for x in self.keys()}
        # match DKeyFormatter.expand(self, sources=(expanded_keys, *sources), fallback=fallback or self._exp_fallback, max=max or self._max_expansions):
        match DKeyFormatter.expand(self, sources=sources, fallback=fallback or self._exp_fallback, max=max or self._max_expansions):
            case None:
                return None
            case DKey() as x if self._exp_type is str:
                return f"{x:w}"
            case x:
                return x

    def _check_expansion(self, value, override=None):
        """ typecheck an expansion result """
        match override or self._typecheck:
            case x if x == Any:
                pass
            case types.GenericAlias() as x:
                if not isinstance(value, x.__origin__):
                    raise TypeError("Expansion value is not the correct container", x, value, self)
                if len((args:=x.__args__)) == 1 and not all(isinstance(y, args[0]) for y in value):
                    raise TypeError("Expansion value does not contain the correct value types", x, value, self)
            case types.UnionType() as x if not isinstance(value, x):
                raise TypeError("Expansion value does not match required type", x, value, self)
            case type() as x if not isinstance(value, x):
                raise TypeError("Expansion value does not match required type", x, value, self)
            case _:
                pass

    def _expansion_hook(self, value) -> Any:
        return value

    def _update_expansion_params(self, mark:MARKTYPE) -> Self:
        """ pre-register expansion parameters """
        match self._mark:
            case None:
                pass
            case _ if self._exp_type is not identity:
                pass
            case DKeyMark_e.PATH:
                self._exp_type  = pl.Path
                self._typecheck = pl.Path
            case DKeyMark_e.STR:
                self._exp_type  = str
                self._typecheck = str
            case DKeyMark_e.TASK:
                self._exp_type  = TaskName.build
                self._typecheck = TaskName

        match self._exp_type:
            case type() as x if issubclass(x, Buildable_p):
                self._typecheck = x
                self._exp_type  = x.build

        return self

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

    def __init_subclass__(cls, *, mark:None|MARKTYPE=None, tparam:None|str=None, multi=False):
        super().__init_subclass__()
        DKey.register_key(cls, mark, tparam=tparam, multi=multi)

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

    def __init__(self, data, fparams:None|str=None, mark:MARKTYPE=None, check:CHECKTYPE=None, ctor:None|type|callable=None, help:None|str=None, fallback=None, max_exp=None, **kwargs):
        super().__init__(data)
        self._exp_type       = ctor or identity
        self._typecheck      = check or Any
        self._mark           = mark or DKeyMark_e.FREE
        self._exp_fallback   = fallback
        self._max_expansions = max_exp

        self._update_expansion_params(mark)
        self.set_fparams(fparams)
        self.set_help(help)

    def __call__(self, *args, **kwargs) -> Any:
        """ call expand on the key """
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

    def set_help(self, help:None|str) -> Self:
        match help:
            case None:
                pass
            case str():
                self._help = help

        return self

    def keys(self) -> list:
        """ Get subkeys of this key. by default, an empty list """
        return []

    @property
    def multi(self) -> bool:
        return False

##-- core

class SingleDKey(DKeyBase, mark=DKeyMark_e.FREE):
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
            result = result.removesuffix(REDIRECT_SUFFIX)
        elif not result.endswith(REDIRECT_SUFFIX):
            result = f"{result}{REDIRECT_SUFFIX}"

        if wrap:
            result = "".join(["{", result, "}"])

        return format(result, rem)

class MultiDKey(DKeyBase, mark=DKeyMark_e.MULTI, multi=True):
    """
      Multi keys allow contain 1+ explicit subkeys
    """

    def __init__(self, data:str|pl.Path, *, mark:MARKTYPE=None, **kwargs):
        super().__init__(data, mark=mark, **kwargs)
        has_text, s_keys = DKeyFormatter.Parse(data)
        self._has_text   = has_text
        self._subkeys = [DKey(key.key, fparams=key.format, cparams=key.conv, implicit=True) for key in s_keys]
        self._unnamed = self.format("", state={key.key : "{}" for key in s_keys})

    def __format__(self, spec:str):
        """
          Multi keys have no special formatting

          ... except stripping dkey particular format specs out of the result?
        """
        rem, wrap, direct = self._consume_format_params(spec)
        return format(str(self), rem)

    def keys(self) -> list[Key_p]:
        return self._subkeys

    def expand(self, *sources, **kwargs) -> Any:
        match self.keys():
            case [RedirectionDKey() as x]:
                return self._expansion_hook(x.expand(*sources, full=True, **kwargs))
            case [x] if not self._has_text:
                return self._expansion_hook(x.expand(*sources, **kwargs))
            case _ if any(isinstance(sub, PathSingleDKey) for sub in self._subkeys):
                return super().expand(*sources, doot.locs, **kwargs)
            case _:
                return super().expand(*sources, **kwargs)

    @property
    def multi(self) -> bool:
        return True

class NonDKey(DKeyBase, mark=DKeyMark_e.NULL):
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

    def _update_expansion_params(self, *args) -> Self:
        self._exp_type  = str
        self._typecheck = str
        return self

##-- end core

##-- specialisations


class StrDKey(SingleDKey, mark=DKeyMark_e.STR, tparam="s"):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._exp_type  = str
        self._typecheck = str

class TaskNameDKey(SingleDKey, mark=DKeyMark_e.TASK, tparam="t"):
    _mark = DKey.mark.TASK

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._exp_type  = TaskName.build
        self._typecheck = TaskName

class RedirectionDKey(SingleDKey, mark=DKeyMark_e.REDIRECT, tparam="R"):
    """
      A Key for getting a redirected key.
      eg: RedirectionDKey(key_) -> SingleDKey(value)

      re_mark :
    """

    _mark = DKey.mark.REDIRECT

    def __init__(self, data, multi=False, re_mark=None, **kwargs):
        super().__init__(data, **kwargs)
        self.multi_redir = multi
        self.re_mark     = re_mark
        self._exp_type  = DKey
        self._typecheck = DKey | list[DKey]

    def expand(self, *sources, fallback=None, max=None, check=None, full:bool=False, **kwargs) -> None|Any:
        match super().redirect(*sources, multi=self.multi_redir, re_mark=self.re_mark):
            case list() as xs if self.multi_redir and full:
                return [x.expand(*sources) for x in xs]
            case list() as xs if self.multi_redir:
                return xs
            case [x, *xs] if full:
                return x.expand(*sources)
            case [x, *xs]:
                return x


class ConflictDKey(SingleDKey):
    """ Like a redirection key,
      but for handling conflicts between subkeys in multikeys.

      eg: MK(--aval={blah!p}/{blah})
    """

class ArgsDKey(SingleDKey, mark=DKeyMark_e.ARGS):
    """ A Key representing the action spec's args """
    _mark = DKey.mark.ARGS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._exp_type  = list
        self._typecheck = list

    def expand(self, *sources, **kwargs) -> list:
        for source in sources:
            if not isinstance(source, SpecStruct_p):
                continue

            return source.args

        return []

class KwargsDKey(SingleDKey, mark=DKeyMark_e.KWARGS):
    """ A Key representing all of an action spec's kwargs """

    _mark = DKey.mark.KWARGS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._exp_type  = dict
        self._typecheck = dict

    def expand(self, *sources, fallback=None, **kwargs) -> dict:
        for source in sources:
            if not isinstance(source, SpecStruct_p):
                continue

            return source.kwargs

        return fallback or dict()

class ImportDKey(SingleDKey, mark=DKeyMark_e.CODE, tparam="c"):
    """
      Subclass for dkey's which expand to CodeReferences
    """
    _mark = DKey.mark.CODE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._exp_type  = CodeReference.build
        self._typecheck = CodeReference

class PathSingleDKey(SingleDKey, mark=DKeyMark_e.PATH):
    """ for paths that are just a single key of a larger string
    eg: `temp`
    """
    _mark = DKey.mark.PATH

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._exp_type  = pl.Path
        self._typecheck = pl.Path

    def expand(self, *sources, fallback=None, **kwargs) -> None|Any:
        """ Expand subkeys, format the multi key
          Takes a variable number of sources (dicts, tomlguards, specs, dootlocations..)
        """
        return super().expand(*sources, doot.locs, fallback=fallback, **kwargs)

    def _expansion_hook(self, value) -> pl.Path|None:
        match value:
            case None:
                return None
            case _:
                return doot.locs.normalize(pl.Path(value))

class PathMultiDKey(MultiDKey, mark=DKeyMark_e.PATH, tparam="p", multi=True):
    """
    A MultiKey that always expands as a path,
    eg: `{temp}/{name}.log`
    """
    _mark = DKey.mark.PATH

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._has_text = True # ensures keys expand fully
        self._exp_type  = pl.Path
        self._typecheck = pl.Path

    def expand(self, *sources, fallback=None, **kwargs) -> None|Any:
        """ Expand subkeys, format the multi key
          Takes a variable number of sources (dicts, tomlguards, specs, dootlocations..)
        """
        return super().expand(*sources, doot.locs, fallback=fallback, **kwargs)

    def _expansion_hook(self, value):
        return doot.locs.normalize(pl.Path(value))

class PostBoxDKey(SingleDKey, mark=DKeyMark_e.POSTBOX, tparam="b"):
    """ A DKey which expands from postbox tasknames  """
    _mark = DKey.mark.POSTBOX

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._exp_type  = list
        self._typecheck = list

    def expand(self, *sources, fallback=None, **kwargs):
        # expand key to a task name
        target = None
        # get from postbox
        result = None
        # return result
        raise NotImplementedError()

##-- end specialisations
