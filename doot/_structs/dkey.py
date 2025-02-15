#!/usr/bin/env python2
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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from pydantic import BaseModel, Field, field_validator, model_validator
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.strang import CodeReference
from jgdv.structs.dkey import DKeyFormatter, DKey, DKeyMark_e, SingleDKey, MultiDKey, NonDKey, DKeyExpansionDecorator
from jgdv.structs.dkey import DKeyed as DKeyed_Base
from jgdv.structs.dkey._expander import ExpInst
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import SpecStruct_p, Buildable_p
from doot._structs.task_name import TaskName

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, Generic, cast, assert_type, assert_never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
   from jgdv import Maybe, Ident, Method, Func, Decorator
   from typing import Final
   from typing import ClassVar, Any, LiteralString
   from typing import Never, Self, Literal
   from typing import TypeGuard
   from collections.abc import Iterable, Iterator, Callable, Generator
   from collections.abc import Sequence, Mapping, MutableMapping, Hashable

   from doot._abstract.protocols import Key_p

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

STATE_TASK_NAME_K                           = doot.constants.patterns.STATE_TASK_NAME_K

class TaskNameDKey(SingleDKey['taskname'],   conv="t"):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = TaskName
        self._typecheck       = TaskName

class PathSingleDKey(DKey[DKeyMark_e.PATH]):
    """ for paths that are just a single key of a larger string
    eg: `temp`
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = pl.Path
        self._typecheck       = pl.Path
        self._relative        = kwargs.get('relative', False)

    def exp_extra_sources(self) -> list:
        return [doot.locs.Current]

    def exp_final_hook(self, val, opts):
        relative = opts.get("relative", False)
        match val:
            case DKey.ExpInst(val=pl.Path() as x) if relative and x.is_absolute():
                raise ValueError("Produced an absolute path when it is marked as relative", x)
            case DKey.ExpInst(val=pl.Path() as x) if relative:
                x.literal = True
                return x
            case DKey.ExpInst(val=pl.Path() as x):
                logging.debug("Normalizing Single Path Key: %s", x)
                val.val = doot.locs.Current.normalize(x)
                val.literal = True
                return val
            case x:
                raise TypeError("Path Expansion did not produce a path", x)

class PathMultiDKey(MultiDKey[DKeyMark_e.PATH], conv="p", multi=True):
    """
    A MultiKey that always expands as a path,
    eg: `{temp}/{name}.log`
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = pl.Path
        self._typecheck       = pl.Path
        self._relative        = kwargs.get('relative', False)

    def exp_extra_sources(self) -> list:
        return [doot.locs.Current]

    def exp_final_hook(self, val, opts) -> Maybe[pl.Path]:
        relative = opts.get("relative", False)
        match val:
            case DKey.ExpInst(val=pl.Path() as x) if relative and x.is_absolute():
                raise ValueError("Produced an absolute path when it is marked as relative", x)
            case DKey.ExpInst(val=pl.Path() as x)  if relative:
                return x
            case DKey.ExpInst(val=pl.Path() as x):
                logging.debug("Normalizing Single Path Key: %s", x)
                return doot.locs.Current.normalize(x)
            case x:
                raise TypeError("Path Expansion did not produce a path", x)

class DootDKeyExpander(DKeyExpansionDecorator):
    """ a doot specific expander that also injects the global task state"""

    def _wrap_method(self, fn:Method) -> Method:
        data_key = self._data_key

        def method_action_expansions(_self, spec, state, *call_args, **kwargs) -> Method:
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

        def fn_action_expansions(spec, state, *call_args, **kwargs) -> Func:
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

class DootKeyed(DKeyed_Base):
    """ Extends jgdv.structs.dkey.DKeyed to handle additional decoration types
    specific for doot
    """
    _decoration_builder : ClassVar[type] = DootDKeyExpander

    @classmethod
    def taskname(cls, fn) -> Decorator:
        keys = [DKey(STATE_TASK_NAME_K, implicit=True, mark=DKey.Mark.TASK)]
        return cls._build_decorator(keys)(fn)
