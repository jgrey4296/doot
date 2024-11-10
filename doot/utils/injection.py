#!/usr/bin/env python2
"""

See EOF for license/metadata/notes as applicable
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

import doot
from tomlguard import TomlGuard
from doot.structs import DKey, TaskSpec
from doot._structs.relation_spec import RelationSpec
##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

T                                = TypeVar("T")
Maybe                            = None | T
Result                           = T | Exception
Data                             = dict | TomlGuard

CLI_K         : Final[str]       = "cli"
MUST_INJECT_K : Final[str]       = "must_inject"
SPECIAL_KEYS  : Final[list[str]] = [CLI_K, MUST_INJECT_K]
INJECT_GROUPS : Final[list[str]] = ["copy", "delay", "expand", "now", "replace", "insert"]

class Injector_m:
    """ Generalized mixin for building injections.
    Injections are of the form {copy:dict|list, expand:dict|list, replace:list}

    Copy/delay     : l_1 key expansions to the new state for expansion later
    Expand/now     : fully expand using current state
    Replace/insert : place literal value insertion into state

    Only the values of the return dict can be expanded
    (ie: { DKey('aval') : 5 }, aval is not expanded )
    """

    def build_injection(self, base:Maybe[RelationSpec|dict], *sources, insertion=None, constraint:Maybe[TaskSpec|Data]=None) -> Maybe[dict]:
        match base:
            case None | RelationSpec(inject=None):
                return None
            case dict():
                base_data = base
            case RelationSpec(inject=str() as base_s):
                base_k = DKey(base_s, implicit=True, check=dict|TomlGuard)
                base_data = base_k(*sources)
            case RelationSpec(inject=dict() as base_data):
                pass
            case _:
                raise TypeError("Unknown injection base type", base)

        match constraint:
            case None:
                constraint_data = {}
            case dict() | TomlGuard():
                constraint_data = constraint_data
            case TaskSpec():
                constraint_data = constraint.extra
            case _:
                raise TypeError("Unknown constraint data type", constraint)

        self._validate_base_format(base_data)

        proposed = self._build_fresh_state(base_data, *sources, insertion=insertion)
        self._validate_keys(set(proposed.keys()), constraint_data)

        injection = {}
        injection.update({cli.name : cli.default for cli in constraint_data.get(CLI_K, [])})
        injection.update({k:v for k,v in constraint_data.items() if k not in SPECIAL_KEYS})
        injection.update(proposed)

        return injection

    def _build_fresh_state(self, inject:Data, *sources, insertion=None) -> Maybe[dict]:
        """ builds a fresh state without worrying about conforming to a spec"""
        match self._split_injection_base(inject):
            case None:
                return None
            case delay, now, insert:
                pass
            case _:
                raise doot.errors.DootActionError("wrong format for replacement injection, should be a list of keys")

        injection_dict = {}
        injection_dict.update({k:v(*sources, max=1) for k,v in delay.items()})
        injection_dict.update({k:v(*sources) for k,v in now.items()})
        if insertion:
            injection_dict.update({k:insertion for k in insert})

        return injection_dict

    def _split_injection_base(self, base:Maybe[Data]) -> Maybe[tuple[dict, dict, list]]:
        """ get the copy,expand and replace data of the proposed injection
        """
        match base:
            case None:
                return None
            case dict() | TomlGuard():
                copy    = self._prep_keys(base.get("delay", None) or base.get("copy", []))
                expand  = self._prep_keys(base.get("now", None) or base.get("expand", []))
                replace = [DKey(x, implicit=True) for x in base.get("replace", [])]
                return copy, expand, replace
            case _:
                raise doot.errors.DootActionError("Wrong format to state injection, should be {copy=dict|list, expand=dict|list, replace=list}", base)

    def _prep_keys(self, keys:dict[str,str]|list[str]) -> dict[str, DKey]:
        """ prepare keys for the expansions """
        match keys:
            case [*xs]:
                return {(k:=DKey(x, implicit=True)):k for x in xs}
            case dict():
                return {DKey(k, implicit=True):DKey(v, implicit=True) for k,v in keys.items()}
            case _:
                raise TypeError("unknown keys type", keys)

    def _validate_keys(self, inject_keys:set[str], spec:dict|TomlGuard) -> None:
        spec_keys = {str(x) for x in inject_keys}
        spec_keys.update({cli.name for cli in spec.get(CLI_K, [])})
        missing   = inject_keys - spec_keys

        if bool(spec) and bool(missing):
            raise doot.errors.DootTaskTrackingError("Can not inject keys not found in the control spec", missing)

        if bool({k for k in spec.get(MUST_INJECT_K, []) if k not in inject_keys}):
            # TODO Some injections were not provided
            pass

    def _validate_base_format(self, base:dict):
        if bool(base.keys() - INJECT_GROUPS):
            raise doot.errors.DootActionError("Wrong format to state injection, should be {copy=dict|list, expand=dict|list, replace=list}", base)

    def match_with_constraints(self, instance:TaskSpec, control:TaskSpec, *, relation:None|RelationSpec=None) -> bool:
        """ Test {instance} against a {control}.
          relation provides the constraining keys that {self} must have in common with {control}.

          if not given a relation, then just check self and control dont conflict.
          """
        match relation:
            case RelationSpec(constraints=con, inject=inj) if not con and not inj:
                return True
            case RelationSpec(constraints=constraints, inject=str() as inject_s):
                inject_k = DKey(inject_s, check=dict|TomlGuard, implicit=True)
                assert(relation.target <= instance.name or any(relation.target <= x for x in instance.get_source_names()))
                inject_d = inject_k(instance)
            case RelationSpec(constraints=constraints, inject=inject_d):
                assert(relation.target <= instance.name or any(relation.target <= x for x in instance.get_source_names()))
                inject_d = inject_d or {}
            case None:
                assert(control.name <= instance.name)
                constraints = {x:x for x in control.extra.keys()}
                inject_d    = {}
            case _:
                raise TypeError("unkown relation type", relation)

        self._validate_base_format(inject_d)
        inject              = {}
        constraints         = constraints or {}
        for y in inject_d.values():
            match y:
                case dict():
                    inject.update(y.items())
                case [*ys]:
                    inject.update({yv:yv for yv in ys})

        instance_data, control_data = instance.extra, control.extra
        if bool(inject) and not bool(inject.values() & control_data.keys()):
            # Theres no overlap between the injection and control
            return False

        for k,v in constraints.items():
            if k not in instance_data or v not in control_data:
                # constraint can't be fulfilled
                return False
            if instance_data[k] != control_data[v]:
                # constraint fails
                return False

        for k,v in inject.items():
            if instance_data.get(k, None) != control_data.get(v, None):
                # injection keys dont match
                return False
        else:
            return True
