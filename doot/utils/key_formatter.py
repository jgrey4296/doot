#!/usr/bin/env python3
"""

key formatting:

- key.format()
- "{}".format(key)
- format(key, spec)

key -> str:
keep as a key if missing.
{x} -> {x}

expand to string if not missing:
{x} -> blah
respect format specs if not missing:
{x: <5} -> 'blah  '
keep format specs if missing:
{x: <5} -> {x: <5}


-----

key expansion:
- key.expand(fmtspec, spec=actionspec, state=state)
- key(spec, state)

key -> str by default.

key -> path|type if conversion spec
{x!p} -> pl.Path...
{x!t} -> dict() etc..



----

format(DKey, fmt) -> DKey.__format__ -> str
DKey.__format__   -> str
Dkey.format       -> KeyFormatter.fmt -> KF.expand -> KF.format -> str
DKey.expand       -> KF.expand -> KF.format -> KF.expand -> Any


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


def chained_get(key:str, *sources:dict|DootLocations) -> Any:
    """
      Get a key's value from an ordered sequence of potential sources
    """
    for source in sources:
        if source is None:
            continue
        replacement = source.get(key, None)
        if replacement is not None:
            return replacement

    return None

class KeyFormatter(string.Formatter):
    """
      A Formatter for expanding arguments based on action spec kwargs, and task state, and cli args

      Extends the format specification mini-language
      (https://docs.python.org/3/library/string.html#format-specification-mini-language)
      with:

      !t : type formatting  eg: '{x!t}'+{x:dict(a=2,b=3)}    -> 'dict(a=2,b=3)'
      !p : path formatting. eg: '{x!p}'+{x:pl.Path(a/b/c)}   -> {cwd}/a/b/c
      !_ : key redirection. eg: '{x!_}'+{x_:blah, blah:bloo} -> {blah}
      !k : as key,          eg: '{x!k}'+{x:blah, blah:bloo}  -> '{bloo}'
      !CR : as coderef      eg: '{x!cr}'+{x:'doot.utils.key_formatter:KeyFormatter} -> KeyFormatter

      and formating controls:

      :.[0-9] : using precision for amount of recursive expansion
      :#      : using alt form for 'direct' key
      :#_     : indirect key form
      :...!   : bang at end of format spec means insist on expansion

      Used for DootKey.__format__
      format(DootKey, spec)
      DootKey.expand
      and '{spec}'.format(DootKey)

      Keys can have a number of forms:
      {x}  : Direct Expansion form
      {x_} : Indirect Expansion form
      x    : Name form, no expansion




    """
    _fmt                = None

    SPEC   : Final[str] = "_spec"
    INSIST : Final[str] = "_insist"
    STATE  : Final[str] = "_state"
    LOCS   : Final[str] = "_locs"
    REC    : Final[str] = "_rec"

    @staticmethod
    def fmt(fmt:str|Key_p|pl.Path, /, *args, **kwargs) -> str:
        """ static method to a singleton key formatter """
        if not KeyFormatter._fmt:
            KeyFormatter._fmt = KeyFormatter()

        return KeyFormatter._fmt.format(fmt, *args, **kwargs)

    @staticmethod
    def exp(fmt:str|Key_p|pl.Path, **kwargs) -> str:
        """ static method to a singleton key formatter """
        if not KeyFormatter._fmt:
            KeyFormatter._fmt = KeyFormatter()

        return KeyFormatter._fmt.expand(fmt=fmt, **kwargs)

    def format(self, fmt:str|Key_p|pl.Path, /, *args, **kwargs) -> str:
        """ expand and coerce keys """
        self._depth = 0
        match kwargs.get(self.SPEC, None):
            case None:
                kwargs['_spec'] = {}
            case x if hasattr(x, "params"):
                kwargs['_spec'] = x.params
            case x:
                raise TypeError("Bad Spec Type in Format Call", x)

        match fmt:
            case Key_p():
                fmt = fmt.form
                result = self.vformat(fmt, args, kwargs)
            case str():
                result = self.vformat(fmt, args, kwargs)
            # case pl.Path():
            #     result = str(ftz.reduce(pl.Path.joinpath, [self.vformat(x, args, kwargs) for x in fmt.parts], pl.Path()))
            case _:
                raise TypeError("Unrecognized expansion type", fmt)

        return result

    def expand(self, *, fmt=None, spec=None, state=None) -> Any:
        raise NotImplementedError()

    def get_value(self, key, args, kwargs) -> str:
        """ lowest level handling of keys being expanded """
        logging.debug("Expanding: %s", key)
        if isinstance(key, int):
            return args[key]

        insist                = kwargs.get(self.INSIST, False)
        spec  : dict          = kwargs.get(self.SPEC, None) or {}
        state : dict          = kwargs.get(self.STATE, None) or {}
        locs  : DootLocations = kwargs.get(self.LOCS,  None)
        depth_check           = self._depth < MAX_KEY_EXPANSIONS
        rec_allowed           = kwargs.get(self.REC, False) and depth_check

        match (replacement:=chained_get(key, spec, state, locs)):
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

    def to_basic_expansion(self, spec=None, state=None, *, on_fail=Any, locs:DootLocations=None, **kwargs) -> str:
        key = self.to_redirection(spec)
        try:
            return self.fmt(key[0], _spec=spec, _state=state, _rec=rec, _locs=locs, _insist=insist)
        except (KeyError, TypeError, IndexError) as err:
            if on_fail != Any:
                return on_fail

            raise err

    def to_type(self, spec:None|SpecStruct_p=None, state=None, type_=Any, on_fail=Any) -> Any:
        target            = self.to_redirection(spec)

        match spec:
            case _ if hasattr(spec, "params"):
                kwargs = spec.params
            case None:
                kwargs = {}

        task_name = state.get(STATE_TASK_NAME_K, None) if state else None
        match (replacement:=chained_get(target[0], kwargs, state)):
            case None if on_fail != Any and isinstance(on_fail, DootKey):
                return on_fail.to_type(spec, state, type_=type_)
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

    def to_path(self, spec=None, state=None, *, locs:DootLocations=None, on_fail:None|str|pl.Path|DootKey=Any, symlinks=False) -> pl.Path:
        """
          Convert a key to an absolute path, using registered locations

          The Process is:
          1) redirect the given key if necessary
          2) Expand each part of the keypath, using KeyFormatter
          3) normalize it

          If necessary, a fallback chain, and on_fail value can be provided
        """
        locs                 = locs or doot.locs
        key : pl.Path        = pl.Path(self.redirect(spec).form)

        try:
            expanded         : list       = [KeyFormatter.fmt(x, _spec=spec, _state=state, _rec=True, _locs=locs) for x in key.parts]
            expanded_as_path : pl.Path    = pl.Path().joinpath(*expanded) # allows ("a", "b/c") -> "a/b/c"

            if bool(matches:=PATTERN.findall(str(expanded_as_path))):
                raise doot.errors.DootLocationExpansionError("Missing keys on path expansion", matches, self)

            return locs.normalize(expanded_as_path, symlinks=symlinks)

        except doot.errors.DootLocationExpansionError as err:
            match on_fail:
                case None:
                    return None
                case DootKey():
                    return on_fail.to_path(spec, state, symlinks=symlinks)
                case pl.Path() | str():
                    return locs.normalize(pl.Path(on_fail),  symlinks=symlinks)
                case _:
                    raise err

    def to_coderef(self, spec:None|SpecStruct_p, state) -> None|CodeReference:
        match spec:
            case _ if hasattr(spec, "params"):
                kwargs = spec.params
            case None:
                kwargs = {}

        redir = self.redirect(spec)

        if redir not in kwargs and redir not in state:
            return None
        try:
            expanded = self.expand(spec, state)
            ref = CodeReference.build(expanded)
            return ref
        except doot.errors.DootError:
            return None

    def to_expansion_form(self, key):
        """ Return the key in its use form, ie: wrapped in braces """
        return "{{{}}}".format(str(key))

    def to_redirection(self, spec:None|SpecStruct_p=None) -> list[str]:
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
        # TODO merge into to_redirection
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
