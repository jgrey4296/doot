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
from jgdv.structs.dkey import ExpInst_d
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
##-- end logging

STATE_TASK_NAME_K                           = doot.constants.patterns.STATE_TASK_NAME_K

class TaskNameDKey(SingleDKey['taskname'],   conv="t"):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = TaskName
        self._typecheck       = TaskName

class DootPathSingleDKey(DKey[DKeyMark_e.PATH]):
    """ for paths that are just a single key of a larger string
    eg: `temp`
    """
    _extra_kwargs : ClassVar[set[str]] = {"relative"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = pl.Path
        self._typecheck       = pl.Path
        self._relative        = kwargs.get('relative', False)

    def exp_extra_sources_h(self) -> list:
        return [doot.locs.Current]

    def exp_final_h(self, val, opts) -> Maybe[ExpInst_d]:
        relative = opts.get("relative", False)
        match val:
            case ExpInst_d(val=pl.Path() as x) if relative and x.is_absolute():
                raise ValueError("Produced an absolute path when it is marked as relative", x)
            case ExpInst_d(val=pl.Path()) as x if relative:
                x.literal = True
                return x
            case ExpInst_d(val=pl.Path() as x) as v:
                logging.debug("Normalizing Single Path Key: %s", x)
                v.val = doot.locs.Current.normalize(x)
                v.literal = True
                return v
            case x:
                raise TypeError("Path Expansion did not produce a path", x)

class DootPathMultiDKey(MultiDKey[DKeyMark_e.PATH], conv="p", multi=True):
    """
    A MultiKey that always expands as a path,
    eg: `{temp}/{name}.log`
    """
    _extra_kwargs : ClassVar[set[str]] = {"relative"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = pl.Path
        self._typecheck       = pl.Path
        self._relative        = kwargs.get('relative', False)

    def exp_pre_lookup_h(self, sources, opts) -> list:
        match self.keys():
            case []:
                return [[
                    ExpInst_d(val=str(self), literal=True)
                ]]
            case [*xs]:
                return super().exp_pre_lookup_h(sources, opts)



    def exp_extra_sources_h(self) -> list:
        return [doot.locs.Current]

    def exp_final_h(self, val, opts) -> Maybe[ExpInst_d]:
        relative = opts.get("relative", False)
        match val:
            case ExpInst_d(val=pl.Path() as x) if relative and x.is_absolute():
                raise ValueError("Produced an absolute path when it is marked as relative", x)
            case ExpInst_d(val=pl.Path()) as x if relative:
                return x
            case ExpInst_d(val=pl.Path() as x) as v:
                logging.debug("Normalizing Single Path Key: %s", x)
                v.val = doot.locs.Current.normalize(x)
                return v
            case x:
                raise TypeError("Path Expansion did not produce a path", x)

class DootKeyed(DKeyed_Base):
    """ Extends jgdv.structs.dkey.DKeyed to handle additional decoration types
    specific for doot
    """
    _decoration_builder : ClassVar[type] = DKeyExpansionDecorator

    @classmethod
    def taskname(cls, fn) -> Decorator:
        keys = [DKey(STATE_TASK_NAME_K, implicit=True, mark="taskname")]
        return cls._build_decorator(keys)(fn)
