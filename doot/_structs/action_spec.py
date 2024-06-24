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
import more_itertools as mitz
from pydantic import BaseModel, Field, field_validator, model_validator
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import SpecStruct_p, ProtocolModelMeta, Buildable_p
from doot._structs.code_ref import CodeReference
from doot.enums import Report_f, TaskMeta_f

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

ALIASES = doot.aliases.action

class ActionSpec(BaseModel, SpecStruct_p, Buildable_p, metaclass=ProtocolModelMeta, arbitrary_types_allowed=True):
    """
      When an action isn't a full blown class, it gets wrapped in this,
      which passes the action spec to the callable.

      TODO: recogise arg prefixs and convert to correct type.
      eg: path:a/relative/path  -> Path(./a/relative/path)
      path:/usr/bin/python  -> Path(/usr/bin/python)

    """
    do         : None|CodeReference                   = None
    args       : list[Any]                            = []
    kwargs     : TomlGuard                            = Field(default_factory=TomlGuard)
    inState    : set[str]                             = set()
    outState   : set[str]                             = set()
    fun        : None|Callable                        = None

    @staticmethod
    def build(data:dict|list|TomlGuard|ActionSpec, *, fun=None) -> ActionSpec:
        match data:
            case ActionSpec():
                return data
            case list():
                action_spec = ActionSpec(
                    args=data,
                    fun=fun if callable(fun) else None
                    )
                return action_spec

            case dict() | TomlGuard():
                kwargs      = TomlGuard({x:y for x,y in data.items() if x not in ActionSpec.model_fields})
                fun         = data.get('fun', fun)
                action_spec = ActionSpec(
                    do=data.get('do', None),
                    args=data.get('args',[]),
                    kwargs=kwargs,
                    inState=set(data.get('inState', set())),
                    outState=set(data.get('outState', set())),
                    fun=fun,
                    )
                return action_spec
            case _:
                raise doot.errors.DootActionError("Unrecognized specification data", data)

    @field_validator("do", mode="before")
    def _validate_do(cls, val):
        match val:
            case None:
                return None
            case str() if val in ALIASES:
                return CodeReference.build(ALIASES[val])
            case str():
                return CodeReference.build(val)
            case CodeReference():
                return val
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
        if self.inState:
            result.append(f"inState={self.inState}")
        if self.outState:
            result.append(f"outState={self.outState}")

        if self.fun and hasattr(self.fun, '__qualname__'):
            result.append(f"calling={self.fun.__qualname__}")
        elif self.fun:
            result.append(f"calling={self.fun.__class__.__qualname__}")

        return f"<ActionSpec: {' '.join(result)} >"

    def __call__(self, task_state:dict):
        if self.fun is None:
            raise doot.errors.DootActionError("Action Spec has not been finalised with a function", self)

        return self.fun(self, task_state)

    def set_function(self, fun:Action_p|Callable):
        """
          Sets the function of the action spec.
          if given a class, the class is built,
          if given a callable, that is used directly.

        """
        # if the function/class has an inState/outState attribute, add those to the spec's fields
        if hasattr(fun, 'inState') and isinstance(getattr(fun, 'inState'), list):
            self.inState.update(getattr(fun, 'inState'))

        if hasattr(fun, 'outState') and isinstance(getattr(fun, 'outState'), list):
            self.outState.update(getattr(fun, 'outState'))

        if isinstance(fun, type):
            self.fun = fun()
        else:
            self.fun = fun

        if not callable(self.fun):
            raise doot.errors.DootActionError("Action Spec Given a non-callable fun: %s", fun)

    def verify(self, state:dict, *, fields=None):
        pos = "Output"
        if fields is None:
            pos = "Input"
            fields = self.inState
        if all(x in state for x in fields):
            return

        raise doot.errors.DootActionStateError("%s Fields Missing: %s", pos, [x for x in fields if x not in state])

    def verify_out(self, state:dict):
        self.verify(state, fields=self.outState)

    @property
    def params(self):
        return self.kwargs
