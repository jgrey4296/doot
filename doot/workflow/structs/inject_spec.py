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
from .._interface import Task_p, MUST_INJECT_K

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

    With a Task C, the control, and Task T, the target,
    C injects data into T at defined times:
    - from_spec[K1, K2]   : T.spec[K1]  = C.spec[K2]
    - from_state[K1, K2]  : T.state[K1] = C.state[K2]
    - from_target[K0, K2] : T.state[K1_] = T.spec[C.spec[K2]]
    - literal[K1, V]      : T.state[k1] = V

    Injection data can be:
    - list[DKey]            : coerced to dict of {K : K}. Implicit keys
    - dict[k1:str, k2:DKey] : k1 is implicit, k2 is explicit

    """
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
        try:
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

        except ValueError:
            raise doot.errors.InjectionError("Injection LHS Keys need to be implicit", keys) from None
        except TypeError:
            raise doot.errors.InjectionError("Injection RHS Keys need to be explicit", keys) from None

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

    @field_validator("from_spec", mode="before")
    def _validate_from_spec(cls, val:Any) -> dict:
        return cls._prep_keys(val)

    @field_validator("from_state", mode="before")
    def _validate_from_state(cls, val:Any) -> dict:
        return cls._prep_keys(val)

    @field_validator("from_target", mode="before")
    def _validate_from_target(cls, val:Any) -> dict:
        result = cls._prep_keys(val)
        return {f"{x}_":y for x,y in result.items()}

    @field_validator("literal", mode="before")
    def _validate_literal(cls, val:Any) -> dict:
        return cls._prep_keys(val, literal=True)

    def __bool__(self) -> bool:
        return (bool(self.from_spec)
                | bool(self.from_state)
                | bool(self.from_target)
                | bool(self.literal)
                | (self.with_suffix is not None))

    def validate(self, control:Task_p|TaskSpec, target:Task_p|TaskSpec, *, only_spec:bool=False) -> bool:
        """ Ensures this injection is usable with given sources, and given required injections

        eg:
        target(must_inject=['a']),
        control('a'=5)
        Injection(from_spec=['a'])
        The Injection is valid.

        eg:
        target(must_inject=['a']),
        control('d'=9)
        Injection(from_spec=['a'])
        The Injection is invalid, 'a' is missing from the source.

        eg:
        target()
        control('a'=10)
        Injection(from_spec=['a'])
        The Injection is invalid, 'a' is surplus to the task.

        """
        result = self.validate_details(control, target, only_spec=only_spec)
        return not any(bool(x) for x in result.values())

    def validate_details(self, control:Task_p|TaskSpec, target:Task_p|TaskSpec, *, only_spec:bool=False) -> dict:
        """
        validate specs or tasks
        checks from_spec,
        and if given tasks, from_state as well
        """
        control_needs : set  = set(self.from_spec.values())
        target_needs  : set  = set(self.from_spec.keys())
        state_failure : bool = False
        if not only_spec:
            state_failure = bool(self.from_state) and not all(isinstance(x, Task_p) for x in (control, target))
        match control:
            case Task_p():
                control_vals   = control.state
                control_needs |= set(self.from_state.values())
            case _:
                control_vals   = control.extra

        match target:
            case Task_p():
                target_vals   = target.state
                target_needs |= set(self.from_state.keys())
            case _:
                target_vals  = target.extra


        must_inject       = target_vals.get(MUST_INJECT_K, [])

        missing           = control_needs - control_vals.keys()
        surplus           = target_needs  - target_vals.keys()
        control_redirects = set(self.from_target.values()) - control_vals.keys()
        target_redirects  = {y for x in self.from_target.values() if (y:=x(control)) not in target_vals}
        mismatches        = set()
        if not (bool(missing) or bool(surplus)):
            # if nothing is missing, test equality
            mismatches |= {(x,y) for x,y in self.from_spec.items() if x(target_vals) != y(control_vals)}

        return {
            "rhs_missing"     : missing,
            "lhs_surplus"     : surplus,
            "rhs_redirect"    : control_redirects,
            "lhs_redirect"    : target_redirects,
            "mismatches"      : mismatches,
            "state"           : state_failure
        }

    def apply_from_spec(self, control:dict|TaskSpec) -> dict:
        """ Apply values from the control's spec values.

        Fully expands keys in 'from_spec',
        Only partially expands (L1) from 'from_target'
        """
        # logging.info("Applying from_spec injection: %s", control.name)
        data = {}
        for x,y in self.from_spec.items():
            data[str(x)] = y(control)
        for x,y in self.from_target.items():
            data[str(x)] = y(control, insist=True, fallback=y, limit=1)
        else:
            return data

    def apply_from_state(self, control:dict|Task_p) -> dict:
        """ Expand a key using the control state """
        # logging.info("Applying from_state injection: %s", control.name)
        match control:
            case dict() | ChainGuard():
                pdata = control
            case Task_p():
                pdata = control.state
        data = {}
        for x,y in self.from_state.items():
            data[str(x)] = y(pdata)
        else:
            return data

    def apply_literal(self, val:Any) -> dict:
        """ Takes a value and sets it for any keys in self.literal

        Used for job's to insert literal values into a key.
        eg: when mapping filenames to generated tasks
        """
        logging.info("Applying literal injection: %s", val)
        data = {}
        for x,_y in self.literal.items(): # type: ignore
            data[str(x)] = val
        else:
            return data
