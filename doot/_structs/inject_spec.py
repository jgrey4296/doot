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
from doot._structs.task_spec import  TaskSpec
from doot._structs.relation_spec import RelationSpec

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

if TYPE_CHECKING or True:
   from jgdv import Maybe
   from typing import Final
   from typing import ClassVar, Tuple, Any, LiteralString
   from typing import Never, Self, Literal
   from typing import TypeGuard
   from collections.abc import Iterable, Iterator, Callable, Generator
   from collections.abc import Sequence, Mapping, MutableMapping, Hashable

   type ConstraintData = TaskSpec | dict | ChainGuard

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
CLI_K         : Final[str]         = "cli"
MUST_INJECT_K : Final[str]         = "must_inject"
SPECIAL_KEYS  : Final[list[str]]   = [CLI_K, MUST_INJECT_K]
INJECT_KEYS   : Final[list[str]]   = doot.constants.misc.INJECT_KEYS
SUFFIX_KEY    : Final[str]         = "_add_suffix"

# Body:

class InjectSpec(BaseModel):
    """A ConstraintData representation of an injection.

    Injections fall into three groups:
    - now    : immediate key expansions
    - delay  : l1 expansions, ready to expand fully later
    - insert : literal values to inject

    They can be of the form:
    - list[str|DKey]     : where k=j for target[k] = source[j]
    - dict[str:str|DKey] : where k,j for target[k] = source[j]

    RHS keys are *explicit* form

    """
    now          : dict       = Field(default_factory=dict)
    delay        : dict       = Field(default_factory=dict)
    insert       : dict       = Field(default_factory=dict)
    suffix       : Maybe[str] = Field(default=None)

    @classmethod
    def build(cls, data:dict, /, sources:Maybe[Iterable]=None, insertion:Any=None, constraint:Maybe[ConstraintData]=None) -> Maybe[Self]:
        """ builds an InjectSpec from basic data """
        logging.trace("Building Injection: %s", data)
        match data:
            case None | RelationSpec(inject=None):
                return None
            case dict() | ChainGuard():
                pass
            case RelationSpec(inject=str() as base_s):
                base_k = DKey(base_s, implicit=True, check=dict|ChainGuard)
                data   = base_k(*sources)
            case RelationSpec(inject=dict() as data):
                pass
            case _:
                raise doot.errors.InjectionError("Unknown injection base type", data)

        try:
            result             = cls(**data)
        except ValidationError as err:
            logging.detail("Building Injection Failed: %s : %s", data, err)
            raise

        if not bool(result):
            return None

        result.initial_expansion(sources)
        result.set_insertion(insertion)
        result._validate_constraints(constraint)

        return result

    @staticmethod
    def _prep_keys(keys:Maybe[dict[str,str]|list[str]], literal:bool=False) -> dict[str, DKey]:
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

    @field_validator("now", mode="before")
    def _validate_now(cls, val:Any) -> dict:
        return cls._prep_keys(val)

    @field_validator("delay", mode="before")
    def _validate_delay(cls, val:Any) -> dict:
        return cls._prep_keys(val)

    @field_validator("insert", mode="before")
    def _validate_insert(cls, val:Any) -> dict:
        return cls._prep_keys(val, literal=True)

    def __bool__(self) -> bool:
        return (bool(self.now)
                | bool(self.delay)
                | bool(self.insert)
                | (self.suffix is not None))

    def initial_expansion(self, sources:Maybe[Iterable]) -> None:
        """ fully expand 'now' vars, l1 expand 'delay' vars """
        if sources is None:
            return
        self.now   = {k:v(*sources, fallback=v) for k,v in self.now.items()}
        self.delay = {k:DKey(v(*sources, insist=True, fallback=v, limit=1)) for k,v in self.delay.items()}

    def set_insertion(self, insertion:Any) -> None:
        if insertion is None:
            return

        for k in self.insert.keys():
            self.insert[k] = self.insert[k] or insertion

    def as_dict(self, *, constraint:Maybe[ConstraintData]=None, insertion=None) -> dict:
        match self._validate_constraints(constraint):
            case  None:
                constraint_base, cli= {}, {}
            case dict() as constraint_base, dict() as cli:
                pass

        match self.suffix:
            case None:
                suffix = {}
            case x:
                suffix = {SUFFIX_KEY: x}

        match insertion:
            case None:
                insert = self.insert
            case x:
                insert = {k:x for k in self.insert.keys()}

        injection   = {} | self.delay | self.now | insert | suffix
        injection = constraint_base | cli | injection

        return injection

    def _validate_constraints(self, constraint:Maybe[ConstraintData]) -> Maybe[tuple[dict, dict]]:
        """ check the keys to be injected match keys in the default spec """
        match constraint:
            case None:
                return
            case dict() | ChainGuard()  as x if not bool(x):
                return
            case dict() | ChainGuard():
                pass
            case TaskSpec():
                constraint = constraint.extra
            case _:
                raise doot.errors.InjectionError("Unknown constraint data type", constraint)

        logging.trace("Validating Injection against constraint: %s", constraint)

        constraint_defaults = {k:v for k,v in constraint.items() if k != MUST_INJECT_K}
        cli_params          = [ParamSpec(**cli) for cli in constraint.get(CLI_K, [])]
        cli                 = {cli.name : cli.default for cli in cli_params}

        inject_keys         = {} | self.delay.keys() | self.now.keys() | self.insert.keys()

        if not bool(inject_keys):
            return None

        # promote indirect keys to direct when checking
        indirect_keys = {x for x in inject_keys if x.endswith("_")}
        inject_keys -= indirect_keys
        inject_keys |= {x[:-1] for x in indirect_keys}

        spec_keys           = {str(x) for x in constraint_defaults.keys()}
        cli_keys            = set(cli.keys())
        required_keys       = {str(x) for x in constraint.get(MUST_INJECT_K, [])}

        if bool(missing:=required_keys - inject_keys):
            raise doot.errors.InjectionError("Required Keys not injected", missing)

        if bool(surplus:=inject_keys - (spec_keys | cli_keys | required_keys)):
            raise doot.errors.InjectionError("Surplus keys can not be injected", surplus)

        return constraint_defaults, cli
