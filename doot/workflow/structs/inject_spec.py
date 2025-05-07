#!/usr/bin/env python3
"""

"""
# ruff: noqa: FBT001, FBT002, ERA001, TC002, TC003
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
import time
import types
import weakref
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.chainguard import ChainGuard
from jgdv.cli import ParamSpec
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.util.dkey import DKey
from doot.workflow._interface import Task_p

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
import typing
from typing import Generic, cast, assert_type, assert_never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import TYPE_CHECKING, no_type_check, final, override, overload
# from dataclasses import InitVar, dataclass, field
from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError
from jgdv import Maybe

if TYPE_CHECKING:
   from typing import Final
   from typing import ClassVar, Tuple, Any, LiteralString
   from typing import Never, Self, Literal
   from typing import TypeGuard
   from collections.abc import Iterable, Iterator, Callable, Generator
   from collections.abc import Sequence, Mapping, MutableMapping, Hashable

   from .._interface import Task_p
   from .. import TaskName, TaskSpec
   type ConstraintData = TaskSpec | dict | ChainGuard

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:

# Body:

class InjectSpec(BaseModel):
    """A ConstraintData representation of an injection.

    With a Task P, the parent, and Task C, the child,
    P injects data into C at defined times:
    - from_spec   : uses P.spec values
    - from_state  : users P.state values
    - from_target : from C.spec
    - literal     : uses supplied data literally

    from_state and from_target both mean the application of the injection
    is delayed from when the child spec is built, to when it is queued, or run.

    Injection data can be:
    - list[str|DKey]     : for k in list, child[k] = parent[j]
    - dict[str:str|DKey] : for k,j in dict.items, child[k] = parent[j]

    List Keys are *implicit*
    Dict RHS keys are *explicit* form

    """
    from_cli     : dict       = Field(default_factory=dict)
    from_spec    : dict       = Field(default_factory=dict)
    from_state   : dict       = Field(default_factory=dict)
    from_target  : dict       = Field(default_factory=dict)
    literal      : dict       = Field(default_factory=dict)
    with_suffix  : Maybe[str] = Field(default=None)
    _mapping     : dict

    @classmethod
    def build(cls, data:dict) -> Maybe[Self]:
        """ builds an InjectSpec from basic data """
        logging.info("Building Injection: %s", data)
        match data:
            case None | InjectSpec():
                return data
            case dict() | ChainGuard() as x if not bool(x):
                return None
            case dict() | ChainGuard():
                pass
            case _:
                raise doot.errors.InjectionError("Unknown injection base type", data)

        try:
            return cls(**data)
        except ValidationError as err:
            logging.debug("Building Injection Failed: %s : %s", data, err)
            raise

    @staticmethod
    def _prep_keys(keys:Maybe[dict[str,str]|list[str]], literal:bool=False) -> dict[str, Maybe[DKey|str]]:
        """ prepare keys for the expansions
        literal = True : means rhs is not a key
        """
        match keys:
            case None:
                return {}
            case [*xs] if literal:
                return {DKey(k, implicit=True):None for k in keys}
            case [*xs]:
                return {(k:=DKey(x, implicit=True)):k for x in xs}
            case dict() if literal:
                return {DKey(k, implicit=True):v for k,v in keys.items()}
            case dict():
                return {DKey(k, implicit=True):DKey(v, insist=True, fallback=v) for k,v in keys.items()}
            case _:
                raise doot.errors.InjectionError("unknown keys type", keys)

    @model_validator(mode="after")
    def _validate_injection(self) -> Self:
        # Build the target <- source mapping
        self._mapping = dict()
        for x,y in itz.chain(self.from_spec.items(),
                             self.from_state.items(),
                             self.from_target.items(),
                             self.literal.items()):
            self._mapping[str(x)] = str(y)
        else:
            return self

    @field_validator("from_cli", mode="before")
    def _validate_from_cli(cls, val:Any) -> dict:
        return cls._prep_keys(val)

    @field_validator("from_spec", mode="before")
    def _validate_from_spec(cls, val:Any) -> dict:
        return cls._prep_keys(val)

    @field_validator("from_state", mode="before")
    def _validate_from_state(cls, val:Any) -> dict:
        return cls._prep_keys(val)

    @field_validator("from_target", mode="before")
    def _validate_from_target(cls, val:Any) -> dict:
        return cls._prep_keys(val)

    @field_validator("literal", mode="before")
    def _validate_literal(cls, val:Any) -> dict:
        return cls._prep_keys(val, literal=True)


    def __bool__(self) -> bool:
        return (bool(self.from_spec)
                | bool(self.from_state)
                | bool(self.from_target)
                | bool(self.literal)
                | (self.with_suffix is not None))

    def validate_against(self, control:TaskSpec, target:TaskSpec) -> bool:
        """ Ensures this injection is usable with given sources, and given required injections

        eg:
        Task(must_inject=['a']),
        Source('a'=5)
        Injection(from_spec=['a'])
        The Injection is valid.

        eg:
        Task(must_inject=['a']),
        Source('d'=10)
        Injection(from_spec=['a'])
        The Injection is invalid, 'a' is missing from the source.

        eg:
        Task('a'=5)
        Source('a'=10)
        Injection(from_spec=['a'])
        The Injection is invalid, 'a' is surplus to the task.


        """
        if any(x not in control.extra for x in self.from_spec.values()):
            raise ValueError("Control is missing injection sources", control.name, self)
        if any(x not in target.extra for x in self.from_spec.keys()):
            return False

        return True



    def apply_from_spec(self, parent:dict|TaskSpec) -> dict:
        """ Apply values from the parent's spec values.

        Fully expands keys in 'from_spec',
        Only partially expands (L1) from 'from_target'
        """
        # logging.info("Applying from_spec injection: %s", parent.name)
        data = {}
        for x,y in self.from_spec.items():
            data[str(x)] = y(parent)
        for x,y in self.from_target.items():
            data[str(x)] = y(parent, insist=True, fallback=y, limit=1)
        else:
            return data

    def apply_from_state(self, parent:dict|Task_p) -> dict:
        """ Expand a key using the parents state """
        # logging.info("Applying from_state injection: %s", parent.name)
        match parent:
            case dict() | ChainGuard():
                pdata = parent
            case Task_p():
                pdata = parent.state
        data = {}
        for x,y in self.from_state.items():
            data[str(x)] = y(pdata)
        else:
            return data


    def apply_from_cli(self, source:TaskName|str) -> dict:
        data = {}
        source_args = doot.args.on_fail({}).sub[source]() # type: ignore
        for x,y in self.from_cli.items():
            data[str(x)] = y(source_args)
        else:
            return data

    def apply_literal(self, val:Any) -> dict:
        """ Takes a value and sets it for any keys in self.literal  """
        logging.info("Applying literal injection: %s", val)
        data = {}
        for x,_y in self.literal.items(): # type: ignore
            data[str(x)] = val
        else:
            return data
