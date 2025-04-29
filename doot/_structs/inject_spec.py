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
from doot._structs.dkey import DKey

# ##-- end 1st party imports

from . import _interface as API

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

   from doot._abstract import Task_p, Task_d
   from doot.structs import TaskName
   from doot._structs.task_spec import  TaskSpec
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

    def validate_against(self, source:Maybe[list[str]]=None, needed:Maybe[list[str]]=None, target:Maybe[list[str]]=None) -> Maybe[tuple[set[str], set[str]]]:
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
        source  = source or []
        needed  = needed or []
        target  = target or []
        surplus = set() # {x for x in self._mapping.keys() if x in target}
        missing = {y for y in self._mapping.values() if y not in source}
        missing |= {z for z in needed if z not in self._mapping}

        if bool(missing) or bool(surplus):
            return surplus, missing

        return None

    def apply_from_spec(self, parent:TaskSpec) -> dict:
        """ Apply values from the parent's spec values """
        data = {}
        for x,y in self.from_spec.items():
            data[str(x)] = y(parent)
        else:
            return data

    def apply_from_state(self, parent:Task_d) -> dict:
        """ Expand a key using the parents state """
        data = {}
        for x,y in self.from_state.items():
            data[str(x)] = y(parent.state, parent.spec)
        else:
            return data

    def apply_from_target(self, parent:Task_p) -> dict:
        """ An L1 expansion from the parent, to use a child's key as the value """
        data = {}
        for x,y in self.from_target.items():
            data[str(x)] = y(parent.state, parent.spec, insist=True, fallback=y, limit=1)
        else:
            return data

    def apply_from_cli(self, source:TaskName|str) -> dict:
        data = {}
        source_args = doot.args.on_fail({}).sub[source]()
        for x,y in self.from_cli.items():
            data[str(x)] = y(source_args)
        else:
            return data

    def apply_literal(self, source:list|dict) -> dict:
        match source:
            case list():
                pass
            case dict():
                pass
            case x:
                raise TypeError(type(x))

        data = {}
        for x,y in self.literal.items():
            data[str(x)] = y
        else:
            return data
