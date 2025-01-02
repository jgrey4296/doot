#!/usr/bin/env python2
"""

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
from pydantic import BaseModel, Field, field_validator, model_validator
from jgdv import Maybe, Ident
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.strang import CodeReference
from jgdv.structs.dkey import DKeyFormatter, DKey, DKeyMark_e, SingleDKey, MultiDKey, NonDKey, DKeyExpansionDecorator
from jgdv.structs.dkey import DKeyed as DKeyed_Base
from jgdv.structs.dkey import DKeyExpansionDecorator
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import Key_p, SpecStruct_p, Buildable_p
from doot._structs.task_name import TaskName

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

KEY_PATTERN                                 = doot.constants.patterns.KEY_PATTERN
MAX_KEY_EXPANSIONS                          = doot.constants.patterns.MAX_KEY_EXPANSIONS
STATE_TASK_NAME_K                           = doot.constants.patterns.STATE_TASK_NAME_K

CWD_MARKER      : Final[Ident]                = "__cwd"

class DootDKeyExpander(DKeyExpansionDecorator):
    """ a doot specific expander that also injects the global task state"""

    def _wrap_method(self, fn:Method) -> Method:
        data_key = self._data_key

        def method_action_expansions(_self, spec, state, *call_args, **kwargs):
            try:
                expansions = [x(spec, state, doot._global_task_state) for x in getattr(fn, data_key)]
            except KeyError as err:
                logging.warning("Action State Expansion Failure: %s", err)
                return False
            else:
                all_args = (*call_args, *expansions)
                return fn(_self, spec, state, *all_args, **kwargs)

        # -
        return method_action_expansions

    def _wrap_fn(self, fn:Func) -> Func:
        data_key = self._data_key

        def fn_action_expansions(spec, state, *call_args, **kwargs):
            try:
                expansions = [x(spec, state, doot._global_task_state) for x in getattr(fn, data_key)]
            except KeyError as err:
                logging.warning("Action State Expansion Failure: %s", err)
                return False
            else:
                all_args = (*call_args, *expansions)
                return fn(spec, state, *all_args, **kwargs)

        # -
        return fn_action_expansions

class TaskNameDKey(SingleDKey, mark=DKeyMark_e.TASK, tparam="t"):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = TaskName
        self._typecheck = TaskName

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
        return [doot.locs.Current]

    def expand(self, *sources, **kwargs) -> Maybe[pl.Path]:
        """ Expand subkeys, format the multi key
          Takes a variable number of sources (dicts, chainguards, specs, dootlocations..)
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

    def _expansion_hook(self, value) -> Maybe[pl.Path]:
        match value:
            case None:
                return None
            case pl.Path() as x if self._relative and x.is_absolute():
                raise ValueError("Produced an absolute path when it is marked as relative", x)
            case pl.Path() as x if self._relative:
                return x
            case pl.Path() as x:
                logging.debug("Normalizing Single Path Key: %s", value)
                return doot.locs.Current.normalize(x)
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
        return [doot.locs.Current]

    def keys(self) -> list[Key_p]:
        subkeys = [DKey(key.key, fmt=key.format, conv=key.conv, implicit=True) for key in self._subkeys]
        return subkeys

    def expand(self, *sources, fallback=None, **kwargs) -> Maybe[pl.Path]:
        """ Expand subkeys, format the multi key
          Takes a variable number of sources (dicts, chainguards, specs, dootlocations..)
        """
        match super().expand(*sources, fallback=fallback, **kwargs):
            case None:
                return self._fallback
            case pl.Path() as x:
                return x
            case _:
                raise TypeError("Path Key shouldn't be able to produce a non-path")

    def _expansion_hook(self, value) -> Maybe[pl.Path]:
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
                return doot.locs.Current.normalize(x)
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

class DKeyed(DKeyed_Base):
    """ Extends jgdv.structs.dkey.DKeyed to handle additional decoration types
    specific for doot
    """
    _decoration_builder : ClassVar[type] = DootDKeyExpander

    @classmethod
    def taskname(cls, fn):
        keys = [DKey(STATE_TASK_NAME_K, implicit=True, mark=DKey.mark.TASK)]
        return cls._build_decorator(keys)(fn)
