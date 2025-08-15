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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from pydantic import BaseModel, Field, field_validator, model_validator
from jgdv.decorators import DecoratorAccessor_m
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.strang import CodeReference
from jgdv.structs.dkey import DKey, DKeyMark_e, SingleDKey, MultiDKey, NonDKey, DKeyExpansionDecorator
from jgdv.structs.dkey import DKeyed
from jgdv.structs.dkey import ExpInst_d
from jgdv._abstract.protocols.general import SpecStruct_p, Buildable_p
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.workflow.structs.task_name import TaskName

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

   from jgdv.structs.dkey import Key_p
   from jgdv.structs.dkey._util._interface import SourceChain_d, InstructionFactory_p, ExpOpts, ExpInstChain_d

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

##--| Vars
STATE_TASK_NAME_K = doot.constants.patterns.STATE_TASK_NAME_K # type: ignore[attr-defined]
##--|

class TaskNameDKey(DKey, mark=TaskName,  convert="t"):
    __slots__ = ()

    def __init__(self, *args:Any, **kwargs:Any) -> None:
        super().__init__(*args, **kwargs)
        self.data.expansion_type  = TaskName
        self.data.typecheck       = TaskName

class DootPathDKey(DKey[pl.Path], mark=pl.Path, ctor=pl.Path, convert="p", overwrite=True):
    """
    A MultiKey that always expands as a path,
    eg: `{temp}/{name}.log`
    """
    __slots__ = ("_relative",)
    _extra_kwargs : ClassVar[set[str]] = {"relative"}

    def __init__(self, *args:Any, **kwargs:Any) -> None:
        super().__init__(*args, **kwargs)
        self.data.expansion_type  = pl.Path
        self.data.typecheck       = pl.Path
        self._relative            = kwargs.get('relative', False)

    def _multi(self) -> Literal[True]:
        return True

    def exp_extra_sources_h(self, current:SourceChain_d) -> SourceChain_d:
        return current.extend(doot.locs.Current)

    def exp_final_h(self, inst:ExpInst_d, root:Maybe[ExpInst_d], factory:InstructionFactory_p, opts:dict) -> Maybe[ExpInst_d]:
        relative = opts.get("relative", False)
        match inst:
            case ExpInst_d(value=pl.Path() as x) if relative and x.is_absolute():
                as_relative = x.relative_to(doot.locs.root)
                return factory.literal_inst(as_relative)
            case ExpInst_d(value=pl.Path()) as x if relative:
                return x
            case ExpInst_d(value=pl.Path() as x) as v:
                logging.debug("Normalizing Single Path Key: %s", x)
                normed = doot.locs.Current.normalize(x) # type: ignore[attr-defined]
                return factory.literal_inst(normed)
            case x:
                raise TypeError("Path Expansion did not produce a path", x)

class DootKeyed(DecoratorAccessor_m, DKeyed):
    """ Extends jgdv.structs.dkey.DKeyed to handle additional decoration types
    specific for doot
    """
    _decoration_builder : ClassVar[type] = DKeyExpansionDecorator

    @classmethod
    def taskname(cls, fn:Callable) -> Decorator:
        keys    = [DKey[TaskName](STATE_TASK_NAME_K, implicit=True)]
        dec     = cls._build_decorator(keys)
        result  = dec(fn)
        return result
