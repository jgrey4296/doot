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
import weakref
from dataclasses import InitVar, dataclass, field
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from pydantic import BaseModel, Field, field_validator, model_validator
from jgdv import Maybe, Proto
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.strang import CodeReference
from jgdv._abstract.protocols.general import SpecStruct_p, Buildable_p
from jgdv._abstract.protocols.pydantic import ProtocolModelMeta
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never, Any
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, overload, override
# outside of type_checking for pydantic
from jgdv import Func  # noqa: TC002
if TYPE_CHECKING:
    from .. import _interface as API  # noqa: N812
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

ALIASES = doot.aliases.on_fail([]).action

##--| body
class ActionSpec(BaseModel, Buildable_p, metaclass=ProtocolModelMeta, arbitrary_types_allowed=True):
    """
      When an action isn't a full blown class, it gets wrapped in this,
      which passes the action spec to the callable.

      TODO: recogise arg prefixs and convert to correct type.
      eg: path:a/relative/path  -> Path(./a/relative/path)
      path:/usr/bin/python  -> Path(/usr/bin/python)

    """
    do         : Maybe[CodeReference] = Field(default=None)
    args       : list[Any]            = Field(default_factory=list)
    kwargs     : ChainGuard           = Field(default_factory=ChainGuard)
    fun        : Maybe[Func]          = Field(default=None)

    @override
    @classmethod
    def build(cls, data:dict|list|ChainGuard|ActionSpec, *, fun:Maybe[Callable]=None) -> ActionSpec: # type: ignore[override]
        match data:
            case ActionSpec():
                return data
            case list():
                action_spec = cls(
                    args=data,
                    fun=fun if callable(fun) else None,
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
    def _validate_do(cls, val:Maybe[str|CodeReference|Callable]) -> Maybe[CodeReference]:
        aliases : dict[str, str]
        match val:
            case None:
                return None
            case CodeReference():
                return val
            case str() if (aliases:=ALIASES()) and val in aliases:
                alias = aliases[val]
                return CodeReference(alias)
            case str():
                return CodeReference(val)
            case x if callable(x):
                return CodeReference(x)
            case _:
                raise TypeError("Unrecognized action spec do type", val)

    @override
    def __str__(self) -> str:
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
    def params(self) -> ChainGuard:
        return self.kwargs

    def set_function(self, *, fun:Maybe[API.Action_p|Func|type|ImportError]=None) -> None:
        """
          Sets the function of the action spec.
          if given a class, the class is built,
          if given a callable, that is used directly.

        """
        if fun is None:
            assert(self.do is not None)
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

    def verify(self, state:dict, *, fields:Maybe[list[str]]=None) -> None:
        raise NotImplementedError()

    def verify_out(self, state:dict) -> None:
        self.verify(state, fields=self.outState)
