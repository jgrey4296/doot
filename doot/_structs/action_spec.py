#!/usr/bin/env python3
"""

"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from pydantic import BaseModel, Field, field_validator, model_validator
from jgdv import Maybe, Func
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.strang import CodeReference
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import SpecStruct_p, ProtocolModelMeta, Buildable_p

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

ALIASES = doot.aliases.on_fail([]).action

class ActionSpec(BaseModel, SpecStruct_p, Buildable_p, metaclass=ProtocolModelMeta, arbitrary_types_allowed=True):
    """
      When an action isn't a full blown class, it gets wrapped in this,
      which passes the action spec to the callable.

      TODO: recogise arg prefixs and convert to correct type.
      eg: path:a/relative/path  -> Path(./a/relative/path)
      path:/usr/bin/python  -> Path(/usr/bin/python)

    """
    do         : Maybe[CodeReference]                   = None
    args       : list[Any]                              = []
    kwargs     : ChainGuard                             = Field(default_factory=ChainGuard)
    fun        : Maybe[Func]                            = None

    @classmethod
    def build(cls, data:dict|list|ChainGuard|ActionSpec, *, fun=None) -> ActionSpec:
        match data:
            case ActionSpec():
                return data
            case list():
                action_spec = cls(
                    args=data,
                    fun=fun if callable(fun) else None
                    )
                return action_spec

            case dict() | ChainGuard():
                kwargs      = ChainGuard({x:y for x,y in data.items() if x not in ActionSpec.model_fields})
                fun         = data.get('fun', fun)
                action_spec = cls(
                    do=data.get('do', None),
                    args=data.get('args',[]),
                    kwargs=kwargs,
                    fun=fun,
                    )
                return action_spec
            case _:
                raise doot.errors.StructLoadError("Unrecognized specification data", data)

    @field_validator("do", mode="before")
    def _validate_do(cls, val):
        match val:
            case None:
                return None
            case CodeReference():
                return val
            case str() if val in ALIASES():
                return CodeReference(ALIASES()[val])
            case str():
                return CodeReference(val)
            case _:
                raise TypeError("Unrecognized action spec do type", val)

    def __str__(self):
        result = []
        if isinstance(self.do, str):
            result.append(f"do={self.do}")
        elif self.do and hasattr(self.do, '__qualname__'):
            result.append(f"do={self.do.__qualname__}")
        elif self.do:
            result.append(f"do={self.do.__class__.__qualname__}")

        if self.args:
            result.append(f"args={[str(x) for x in self.args]}")
        if self.kwargs:
            result.append(f"kwargs={self.kwargs}")
        if self.fun and hasattr(self.fun, '__qualname__'):
            result.append(f"calling={self.fun.__qualname__}")
        elif self.fun:
            result.append(f"calling={self.fun.__class__.__qualname__}")

        return f"<ActionSpec: {' '.join(result)} >"

    def __call__(self, task_state:dict) -> Any:
        if self.fun is None:
            raise doot.errors.StructError("Action Spec has not been finalised with a function", self)

        return self.fun(self, task_state)

    @property
    def params(self):
        return self.kwargs

    def set_function(self, *, fun:Maybe[Action_p|Func|type|ImportError]=None):
        """
          Sets the function of the action spec.
          if given a class, the class is built,
          if given a callable, that is used directly.

        """
        if fun is None:
            fun = self.do()

        match fun:
            case ImportError() as err:
                raise err from None
            case type() as x:
                self.fun = x()
            case x if callable(x):
                self.fun = fun
            case x:
                raise doot.errors.StructError("Action Spec Given a non-callable fun: %s", fun)

    def verify(self, state:dict, *, fields=None):
        raise NotImplementedError()

    def verify_out(self, state:dict):
        self.verify(state, fields=self.outState)
