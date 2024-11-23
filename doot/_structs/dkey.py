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
from jgdv.structs.code_ref import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.key import DKey, REDIRECT_SUFFIX, CONV_SEP, DKeyMark_e
from doot._abstract.protocols import Key_p, SpecStruct_p, Buildable_p
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
printer = doot.subprinter()
##-- end logging

KEY_PATTERN                                 = doot.constants.patterns.KEY_PATTERN
MAX_KEY_EXPANSIONS                          = doot.constants.patterns.MAX_KEY_EXPANSIONS
STATE_TASK_NAME_K                           = doot.constants.patterns.STATE_TASK_NAME_K

PATTERN         : Final[re.Pattern]         = re.compile(KEY_PATTERN)
FAIL_PATTERN    : Final[re.Pattern]         = re.compile("[^a-zA-Z_{}/0-9-]")
FMT_PATTERN     : Final[re.Pattern]         = re.compile("[wdi]+")
EXPANSION_HINT  : Final[str]                = "_doot_expansion_hint"
HELP_HINT       : Final[str]                = "_doot_help_hint"
FORMAT_SEP      : Final[str]                = ":"
CHECKTYPE       : TypeAlias                 = None|type|types.GenericAlias|types.UnionType
CWD_MARKER      : Final[str]                = "__cwd"

def identity(x):
    return x

##-- expansion and formatting

class DKeyFormatting_m:

    """ General formatting for dkeys """

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

    def format(self, fmt, *, spec=None, state=None) -> str:
        return DKeyFormatter.fmt(self, fmt, **(state or {}))

    def set_fmt_params(self, params:str) -> Self:
        match params:
            case None:
                pass
            case str() if bool(params):
                self._fmt_params = params
        return self

class DKeyExpansion_m:
    """ general expansion for dkeys """

    def redirect(self, *sources, multi=False, re_mark=None, fallback=None, **kwargs) -> list[DKey]:
        """
          Always returns a list of keys, even if the key is itself
        """
        match DKeyFormatter.redirect(self, sources=sources, fallback=fallback):
            case []:
                return [DKey(f"{self:d}", mark=re_mark)]
            case [*xs] if multi:
                return [DKey(x, mark=re_mark, implicit=True) for x in xs]
            case [x] if x is self:
                return [DKey(f"{self:d}", implicit=True)]
            case [x]:
                return [DKey(x, mark=re_mark, implicit=True)]
            case x:
                raise TypeError("bad redirection type", x, self)

    def expand(self, *sources, fallback=None, max=None, check=None, **kwargs) -> None|Any:
        logging.debug("DKey expansion for: %s", self)
        match DKeyFormatter.expand(self, sources=sources, fallback=fallback or self._fallback, max=max or self._max_expansions):
            case None:
                return None
            case DKey() as x if self._expansion_type is str:
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

    def _update_expansion_params(self, mark:DKeyMark_e) -> Self:
        """ pre-register expansion parameters """
        match self._mark:
            case None:
                pass
            case _ if self._expansion_type is not identity:
                pass
            case DKeyMark_e.PATH:
                self._expansion_type  = pl.Path
                self._typecheck = pl.Path
            case DKeyMark_e.STR:
                self._expansion_type  = str
                self._typecheck = str
            case DKeyMark_e.TASK:
                self._expansion_type  = TaskName.build
                self._typecheck = TaskName

        match self._expansion_type:
            case type() as x if issubclass(x, Buildable_p):
                self._typecheck = x
                self._expansion_type  = x.build

        return self

##-- end expansion and formatting

class DKeyBase(DKeyFormatting_m, DKeyExpansion_m, Key_p, str):
    """
      Base class characteristics of DKeys.
      adds:
      `_mark`
      `_expansion_type`
      `_typecheck`

      plus some util methods

    """

    _mark               : DKeyMark_e                  = DKey.mark.default
    _expansion_type     : type|callable               = str
    _typecheck          : CHECKTYPE                   = Any
    _fallback           : Any                         = None
    _fmt_params         : None|str                    = None
    _help               : None|str                    = None

    __hash__                                          = str.__hash__

    def __init_subclass__(cls, *, mark:None|DKeyMark_e=None, tparam:None|str=None, multi=False):
        super().__init_subclass__()
        cls._mark = mark
        DKey.register_key(cls, mark, tparam=tparam, multi=multi)
        DKey.register_parser(DKeyFormatter)

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

    def __init__(self, data, fmt:None|str=None, mark:DKeyMark_e=None, check:CHECKTYPE=None, ctor:None|type|callable=None, help:None|str=None, fallback=None, max_exp=None, **kwargs):
        super().__init__(data)
        self._expansion_type       = ctor or identity
        self._typecheck            = check or Any
        self._mark                 = mark or DKeyMark_e.FREE
        self._fallback             = fallback
        self._max_expansions       = max_exp
        if self._fallback is Self:
            self._fallback = self

        self._update_expansion_params(mark)
        self.set_fmt_params(fmt)
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

    def keys(self) -> list[Key_p]:
        """ Get subkeys of this key. by default, an empty list """
        return []

    def extra_sources(self) -> list[Any]:
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

    def __init__(self, data:str|pl.Path, *, mark:DKeyMark_e=None, **kwargs):
        super().__init__(data, mark=mark, **kwargs)
        has_text, s_keys = DKeyFormatter.Parse(data)
        self._has_text   = has_text
        self._subkeys    = s_keys
        self._anon    = self.format("", state={key.key : "{}" for key in s_keys})

    def __format__(self, spec:str):
        """
          Multi keys have no special formatting

          ... except stripping dkey particular format specs out of the result?
        """
        rem, wrap, direct = self._consume_format_params(spec)
        return format(str(self), rem)

    def keys(self) -> list[Key_p]:
        return [DKey(key.key, fmt=key.format, conv=key.conv, implicit=True) for key in self._subkeys]

    def expand(self, *sources, **kwargs) -> Any:
        logging.debug("MultiDKey Expand")
        match self.keys():
            case [RedirectionDKey() as x]:
                return self._expansion_hook(x.expand(*sources, full=True, **kwargs))
            case [x] if not self._has_text:
                return self._expansion_hook(x.expand(*sources, **kwargs))
            case _:
                return super().expand(*sources, **kwargs)

    @property
    def multi(self) -> bool:
        return True

class NonDKey(DKeyBase, mark=DKeyMark_e.NULL):
    """
      Just a string, not a key. But this lets you call no-ops for key specific methods
    """

    def __init__(self, data, **kwargs):
        """
          ignores all kwargs
        """
        super().__init__(data)
        if (fb:=kwargs.get('fallback', None)) is not None and fb != self:
            raise ValueError("NonKeys can't have a fallback, did you mean to use an explicit key?", self)

    def __format__(self, spec) -> str:
        rem, _, _ = self._consume_format_params(spec)
        return format(str(self), rem)

    def format(self, fmt) -> str:
        return format(self, fmt)

    def expand(self, *args, **kwargs) -> str:
        if (fb:=kwargs.get('fallback', None)) is not None and fb != self:
            raise ValueError("NonKeys can't have a fallback, did you mean to use an explicit key?", self)
        return str(self)

    def _update_expansion_params(self, *args) -> Self:
        self._expansion_type  = str
        self._typecheck       = str
        return self

##-- end core

##-- specialisations

class StrDKey(SingleDKey, mark=DKeyMark_e.STR, tparam="s"):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = str
        self._typecheck = str

class TaskNameDKey(SingleDKey, mark=DKeyMark_e.TASK, tparam="t"):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = TaskName.build
        self._typecheck = TaskName

class RedirectionDKey(SingleDKey, mark=DKeyMark_e.REDIRECT, tparam="R"):
    """
      A Key for getting a redirected key.
      eg: RedirectionDKey(key_) -> SingleDKey(value)

      re_mark :
    """


    def __init__(self, data, multi=False, re_mark=None, **kwargs):
        kwargs['fallback'] = kwargs.get('fallback', Self)
        super().__init__(data, **kwargs)
        self.multi_redir      = multi
        self.re_mark          = re_mark
        self._expansion_type  = DKey
        self._typecheck       = DKey | list[DKey]

    def expand(self, *sources, max=None, full:bool=False, **kwargs) -> None|DKey:
        match super().redirect(*sources, multi=self.multi_redir, re_mark=self.re_mark, **kwargs):
            case list() as xs if self.multi_redir and full:
                return [x.expand(*sources) for x in xs]
            case list() as xs if self.multi_redir:
                return xs
            case [x, *xs] if full:
                return x.expand(*sources)
            case [x, *xs] if self._fallback == self and x < self:
                return x
            case [x, *xs] if self._fallback is None:
                return None
            case [x, *xs]:
                return x
            case []:
                return self._fallback


class ConflictDKey(SingleDKey):
    """ Like a redirection key,
      but for handling conflicts between subkeys in multikeys.

      eg: MK(--aval={blah!p}/{blah})
    """

class ArgsDKey(SingleDKey, mark=DKeyMark_e.ARGS):
    """ A Key representing the action spec's args """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = list
        self._typecheck = list

    def expand(self, *sources, **kwargs) -> list:
        for source in sources:
            if not isinstance(source, SpecStruct_p):
                continue

            return source.args

        return []

class KwargsDKey(SingleDKey, mark=DKeyMark_e.KWARGS):
    """ A Key representing all of an action spec's kwargs """


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = dict
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = CodeReference.build
        self._typecheck = CodeReference

class PathSingleDKey(SingleDKey, mark=DKeyMark_e.PATH):
    """ for paths that are just a single key of a larger string
    eg: `temp`
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = pl.Path
        self._typecheck       = pl.Path
        self._relative        = kwargs.get('relative', False)

    def extra_sources(self):
        return [doot.locs]

    def expand(self, *sources, **kwargs) -> None|Pl.Path:
        """ Expand subkeys, format the multi key
          Takes a variable number of sources (dicts, tomlguards, specs, dootlocations..)
        """
        logging.debug("Single Path Expand")
        if self == CWD_MARKER:
            return pl.Path.cwd()
        match super().expand(*sources, **kwargs):
            case None:
                return self._fallback
            case pl.Path() as x:
                return x
            case _:
                raise TypeError("Path Key shouldn't be able to produce a non-path")

    def _expansion_hook(self, value) -> None|pl.Path:
        match value:
            case None:
                return None
            case pl.Path() as x if self._relative and x.is_absolute():
                raise ValueError("Produced an absolute path when it is marked as relative", x)
            case pl.Path() as x if self._relative:
                return x
            case pl.Path() as x:
                logging.debug("Normalizing Single Path Key: %s", value)
                return doot.locs.normalize(x)
            case x:
                raise TypeError("Path Expansion did not produce a path", x)

class PathMultiDKey(MultiDKey, mark=DKeyMark_e.PATH, tparam="p", multi=True):
    """
    A MultiKey that always expands as a path,
    eg: `{temp}/{name}.log`
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = pl.Path
        self._typecheck       = pl.Path
        self._relative        = kwargs.get('relative', False)

    def extra_sources(self):
        return [doot.locs]

    def keys(self) -> list[Key_p]:
        subkeys = [DKey(key.key, fmt=key.format, conv=key.conv, implicit=True) for key in self._subkeys]
        return subkeys

    def expand(self, *sources, fallback=None, **kwargs) -> None|pl.Path:
        """ Expand subkeys, format the multi key
          Takes a variable number of sources (dicts, tomlguards, specs, dootlocations..)
        """
        match super().expand(*sources, fallback=fallback, **kwargs):
            case None:
                return self._fallback
            case pl.Path() as x:
                return x
            case _:
                raise TypeError("Path Key shouldn't be able to produce a non-path")

    def _expansion_hook(self, value) -> None|pl.Path:
        logging.debug("Normalizing Multi path key: %s", value)
        match value:
            case None:
                return None
            case pl.Path() as x if self._relative and x.is_absolute():
                raise ValueError("Produced an absolute path when it is marked as relative", x)
            case pl.Path() as x  if self._relative:
                return x
            case pl.Path() as x:
                logging.debug("Normalizing Single Path Key: %s", value)
                return doot.locs.normalize(x)
            case x:
                raise TypeError("Path Expansion did not produce a path", x)

class PostBoxDKey(SingleDKey, mark=DKeyMark_e.POSTBOX, tparam="b"):
    """ A DKey which expands from postbox tasknames  """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = list
        self._typecheck = list

    def expand(self, *sources, fallback=None, **kwargs):
        # expand key to a task name
        target = None
        # get from postbox
        result = None
        # return result
        raise NotImplementedError()

##-- end specialisations
