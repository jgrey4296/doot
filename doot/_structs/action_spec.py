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
from dataclasses import InitVar, dataclass, field
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


import importlib
from tomlguard import TomlGuard
import doot.errors
import doot.constants
from doot.enums import TaskFlags, ReportEnum

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]

@dataclass
class DootActionSpec:
    """
      When an action isn't a full blown class, it gets wrapped in this,
      which passes the action spec to the callable.

      TODO: recogise arg prefixs and convert to correct type.
      eg: path:a/relative/path  -> Path(./a/relative/path)
      path:/usr/bin/python  -> Path(/usr/bin/python)

    """
    do         : None|str                = field(default=None)
    args       : list[Any]               = field(default_factory=list)
    kwargs     : TomlGuard                  = field(default_factory=TomlGuard)
    inState    : set[str]                = field(default_factory=set)
    outState   : set[str]                = field(default_factory=set)
    fun        : None|Callable           = field(default=None)

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
        return self.fun(self, task_state)

    def set_function(self, fun:Action_p|Callable):
        """
          Sets the function of the action spec.
          if given a class, the class it built,
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

    @staticmethod
    def from_data(data:dict|list|TomlGuard|DootActionSpec, *, fun=None) -> DootActionSpec:
        match data:
            case DootActionSpec():
                return data
            case list():
                action_spec = DootActionSpec(
                    args=data,
                    fun=fun if callable(fun) else None
                    )
                return action_spec

            case dict() | TomlGuard():
                kwargs = TomlGuard({x:y for x,y in data.items() if x not in DootActionSpec.__dataclass_fields__.keys()})
                action_spec = DootActionSpec(
                    do=data['do'],
                    args=data.get('args',[]),
                    kwargs=kwargs,
                    inState=set(data.get('inState', set())),
                    outState=set(data.get('outState', set())),
                    fun=fun if callable(fun) else None
                    )
                return action_spec
            case _:
                raise doot.errors.DootActionError("Unrecognized specification data", data)
