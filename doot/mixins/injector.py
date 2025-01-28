#!/usr/bin/env python2
"""

"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import sys
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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.chainguard import ChainGuard
from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot._structs.relation_spec import RelationSpec
from doot.structs import DKey, TaskSpec

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

T                                  = TypeVar("T")
Maybe                              = None | T
Result                             = T | Exception
Data                               = dict | ChainGuard

CLI_K         : Final[str]         = "cli"
MUST_INJECT_K : Final[str]         = "must_inject"
SPECIAL_KEYS  : Final[list[str]]   = [CLI_K, MUST_INJECT_K]
INJECT_KEYS   : Final[list[str]]   = doot.constants.misc.INJECT_KEYS

class Injection_d(BaseModel):
    """A Data representation of an injection."""
    now     : dict
    delay   : dict
    insert  : dict

    @staticmethod
    def build(data:dict, constraint:dict) -> Maybe[Self]:
        """  """
        now             = data.get("now", [])
        delay           = data.get("delay", [])
        insert          = data.get("insert", [])

        cli_dict        = {cli.name : cli.default for cli in constraint.get(CLI_K, [])}
        constraint_dict = {k:v for k,v in constraint.items() if k not in SPECIAL_KEYS}
        result          = Injection_d(now=[],
                                      delay=[],
                                      insert=[])
        # result._validate_key_constraints(set(proposed.keys()), constraint_data)
        return result

    @staticmethod
    def _prep_keys(keys:Maybe[dict[str,str]|list[str]], literal=False) -> dict[str, DKey]:
        """ prepare keys for the expansions """
        match keys:
            case None:
                return {}
            case [*xs]:
                return {(k:=DKey(x, implicit=True)):k for x in xs}
            case dict() if literal:
                return {DKey(k, implicit=True):v for k,v in keys.items()}
            case dict():
                return {DKey(k, implicit=True):DKey(v, implicit=True, fallback=v) for k,v in keys.items()}
            case _:
                raise doot.errors.StateError("unknown keys type", keys)

    @field_validator("now")
    def _validate_now(cls, val):
        return cls._prep_keys(val)

    @field_validator("delay")
    def _validate_delay(cls, val):
        return cls._prep_keys(val)

    @field_validator("insert")
    def _validate_insert(cls, val):
        insert = [DKey(x, implicit=True) for x in base.get("insert", None)]
        insert = {k:insertion for k in insert}
        return val

    def initial_expansion(self, *sources):
        self.now   = {k:v(*sources, fallback=v) for k,v in self.now.items()}
        self.delay = {k:v(*sources, fallback=v, max=1) for k,v in val.items()}

class Injector_m:
    """ Generalized mixin for building injections.
    Injections are of the form {copy:dict|list, expand:dict|list, replace:list}

    delay     : l_1 key expansions to the new state for expansion later
    now       : fully expand using current state
    insert    : place literal value insertion into state

    Only the values of the return dict can be expanded
    (ie: { DKey('aval') : 5 }, aval is not expanded )

    Injections can also add a suffix to the task the inject into, for identification purposes
    """

    def build_injection(self, base:Maybe[RelationSpec|dict], *sources,
                        insertion=None,
                        constraint:Maybe[TaskSpec|Data]=None) -> Maybe[dict|Injection_d]:
        # Extract the initial data used for the injection
        match base:
            case None | RelationSpec(inject=None):
                return None
            case dict() | ChainGuard():
                base_data = base
            case RelationSpec(inject=str() as base_s):
                base_k = DKey(base_s, implicit=True, check=dict|ChainGuard)
                base_data = base_k(*sources)
            case RelationSpec(inject=dict() as base_data):
                pass
            case _:
                raise doot.errors.StateError("Unknown injection base type", base)

        # Get any constraints
        match constraint:
            case None:
                constraint_data = {}
            case dict() | ChainGuard():
                constraint_data = constraint
            case TaskSpec():
                constraint_data = constraint.extra
            case _:
                raise doot.errors.StateError("Unknown constraint data type", constraint)

        # Validate the format


        insert             = Injection_d._prep_keys(base_data.get("insert", None), literal=True)
        now                = Injection_d._prep_keys(base_data.get("now", None))
        delay              = Injection_d._prep_keys(base_data.get("delay", None))
        insert_dict        = {k:insertion or v for k,v in insert.items()}
        # Perform expansions
        now_dict           = {k:v(*sources) for k,v in now.items()}
        delay_dict         = {k:v(*sources, max=1)  for k,v in delay.items()}
        cli_dict           = {cli.name : cli.default for cli in constraint_data.get(CLI_K, [])}
        constraint_dict    = {k:v for k,v in constraint_data.items() if k not in SPECIAL_KEYS}
        injection          = {} | constraint_dict | cli_dict | delay_dict | now_dict | insert_dict
        self._validate_key_constraints(set(injection.keys()), constraint_dict)
        match base_data.get("suffix", None):
            case None:
                pass
            case str() as suff:
                injection['_add_suffix'] = suff

        return injection


    def _validate_key_constraints(self, inject_keys:set[str], spec:dict|ChainGuard) -> None:
        """ check the keys to be injected match keys in the default spec """
        inject_keys   = {str(x) for x in inject_keys}
        spec_keys     = {str(x) for x in spec.keys()}
        cli_keys      = {str(cli.name) for cli in spec.get(CLI_K, [])}
        required_keys = {str(x) for x in spec.get(MUST_INJECT_K, [])}

        if bool(spec_keys) and bool(missing:=required_keys - inject_keys):
            raise doot.errors.StateError("Required Keys not injected", missing)

        if bool(spec_keys) and bool(surplus:=inject_keys - (spec_keys | cli_keys | required_keys)):
            raise doot.errors.StateError("Surplus keys can not be injected", surplus)
