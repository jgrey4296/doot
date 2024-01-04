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

from collections import UserString
import string
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.constants import KEY_PATTERN, MAX_KEY_EXPANSIONS

PATTERN : Final[re.Pattern] = re.compile("{(.+?)}")

class DootKey(str):
    """
      To simplify argument expansion, a str subclass.
      DootKeys are strings, that implicitly are wrapped in {}.
      so DootKey.make("blah") -> DootKey("blah") -> str=="{blah}"

    """

    @staticmethod
    def make(s):
        match s:
            case DootKey():
                return s
            case str() if s[0] == "{" and s[-1] == "}":
                return DootKey(s[1:-1])
            case str() if re.search("{|}", s):
                return s
            case str():
                return DootKey(s)
            case _:
                raise TypeError("Bad Type to build a Doot Key Out of", s)

    def __repr__(self):
        return "<DootKey: {}>".format(str(self))

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        match other:
            case DootKey():
                return str(self) == str(other)
            case str():
                return str(self) == str(other)

    def within(self, other:str|dict|TomlGuard):
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
            return DootKey("{}_".format(super().__str__()))
        return self

    @property
    def is_indirect(self):
        return str(self).endswith("_")

    @property
    def form(self):
        return "{{{}}}".format(str(self))

    def expand(self, spec, state, rec=False) -> str:
        key = self.redirect(spec)
        fmt = DootFormatter()
        return fmt.format(key, _spec=spec, _state=state, _rec=rec)

    def redirect(self, spec, chain=None) -> DootKey:
        """
          If the indirect form of the key is found in the spec, use that instead
        """
        if self.indirect in spec.kwargs:
            return DootKey.make(spec.kwargs[self.indirect])
        if self.is_indirect and self in spec.kwargs:
            return DootKey.make(spec.kwargs[self])
        if chain:
            return chain

        return self

    def to_path(self, spec, state, chain=None) -> pl.Path:
        fmt       = DootFormatter()
        try:
            key       = self.redirect(spec)
            expanded  = fmt.format(key, _spec=spec, _state=state)
            finalised = fmt.format(expanded, _spec=spec, _state=state, _as_path=True)
            return finalised
        except doot.errors.DootLocationExpansionError as err:
            match chain:
                case None:
                    raise err
                case DootKey():
                    return chain.to_path(spec, state)

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
    """ A string of multiple keys """

    def keys(self):
        pass

    def expand(self, spec, state):
        pass

class DootKeyChain(DootKey):
    pass


"""


"""


class DootFormatter(string.Formatter):
    """
      A Formatter for expanding arguments based on both action spec kwargs,
      and task state
    """

    def format(self, fmt, /, *args, _as_path=False, **kwargs) -> str|pl.Path:
        self._depth = 0
        match fmt:
            case DootKey():
                fmt = fmt.form
                result = self.vformat(fmt, args, kwargs)
            case str():
                result = self.vformat(fmt, args, kwargs)
            case pl.Path():
                result = ftz.reduce(pl.Path.joinpath, [self.vformat(x, args, kwargs) for x in fmt.parts], pl.Path())
            case _:
                raise TypeError("Unrecognized expansion type", fmt)

        if _as_path:
            return doot.locs[result]
        return result

    def get_value(self, key, args, kwargs):
        logging.debug("Expanding: %s", key)
        if isinstance(key, int):
            return args[key]

        state             = kwargs.get('_state')
        spec              = kwargs.get('_spec').kwargs
        cli               = doot.args.on_fail({}).tasks[str(state.get('_task_name', None))]()
        replacement       = cli.get(key, None) or state.get(key, None) or spec.get(key, None)
        match replacement:
            case None:
                return DootKey(key).form
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
