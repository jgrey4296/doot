#!/usr/bin/env python2
"""

See EOF for license/metadata/notes as applicable
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
from tomlguard import TomlGuard

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
Data                               = dict | TomlGuard

CLI_K         : Final[str]         = "cli"
MUST_INJECT_K : Final[str]         = "must_inject"
SPECIAL_KEYS  : Final[list[str]]   = [CLI_K, MUST_INJECT_K]
INJECT_GROUPS : Final[list[str]]   = ["copy", "delay", "expand", "now", "replace", "insert"]

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
                raise doot.errors.DootStateError("Unknown injection base type", base)

        match constraint:
            case None:
                constraint_data = {}
            case dict() | TomlGuard():
                constraint_data = constraint
            case TaskSpec():
                constraint_data = constraint.extra
            case _:
                raise doot.errors.DootStateError("Unknown constraint data type", constraint)

        self._validate_injection_dict_format(base_data)

        proposed = self._build_fresh_state(base_data, *sources, insertion=insertion)
        self._validate_key_constraints(set(proposed.keys()), constraint_data)

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
                raise doot.errors.DootStateError("wrong format for replacement injection, should be a list of keys")

        injection_dict = {}
        injection_dict.update({k:v(*sources, fallback=v, max=1) for k,v in delay.items()})
        injection_dict.update({k:v(*sources, fallback=v) for k,v in now.items()})
        if insertion:
            injection_dict.update({k:insertion for k in insert})

        return injection_dict

    def _split_injection_base(self, base:Maybe[Data]) -> Maybe[tuple[dict, dict, list]]:
        """ get the copy,expand and replace data of the proposed injection """
        match base:
            case None:
                return None
            case dict() | TomlGuard():
                copy    = self._prep_keys(base.get("delay", None) or base.get("copy", []))
                expand  = self._prep_keys(base.get("now", None) or base.get("expand", []))
                replace = [DKey(x, implicit=True) for x in base.get("insert", None) or base.get("replace", [])]
                return copy, expand, replace
            case _:
                raise doot.errors.DootStateError("Wrong injection spec type", base)

    def _prep_keys(self, keys:dict[str,str]|list[str]) -> dict[str, DKey]:
        """ prepare keys for the expansions """
        match keys:
            case [*xs]:
                return {(k:=DKey(x, implicit=True)):k for x in xs}
            case dict():
                return {DKey(k, implicit=True):DKey(v, implicit=True) for k,v in keys.items()}
            case _:
                raise doot.errors.DootStateError("unknown keys type", keys)

    def _validate_key_constraints(self, inject_keys:set[str], spec:dict|TomlGuard) -> None:
        """ check the keys to be injected match keys in the default spec """
        inject_keys   = {str(x) for x in inject_keys}
        spec_keys     = {str(x) for x in spec.keys()}
        cli_keys      = {str(cli.name) for cli in spec.get(CLI_K, [])}
        required_keys = {str(x) for x in spec.get(MUST_INJECT_K, [])}

        if bool(spec_keys) and bool(missing:=required_keys - inject_keys):
            raise doot.errors.DootStateError("Required Keys not injected", missing)

        if bool(spec_keys) and bool(surplus:=inject_keys - (spec_keys | cli_keys | required_keys)):
            raise doot.errors.DootStateError("Surplus keys can not be injected", surplus)

    def _validate_injection_dict_format(self, base:dict):
        if bool(base.keys() - INJECT_GROUPS):
            raise doot.errors.DootStateError("Wrong format injection, should be {delay=dict|list, now=dict|list, insert=list}", base)

    def match_with_constraints(self,  target:TaskSpec, control:TaskSpec, *, relation:Maybe[RelationSpec]=None) -> bool:
        """ Test {target} against a {control}.
          relation provides the constraining keys that {self} must have in common with {control}.

          if not given a relation, then just check self and control dont conflict.
          """

        match relation:
            case None if not control.name <= target.name:
                return False
            case RelationSpec(target=targ):
                # the target instance must be more specific than the target mentioned in the relation
                sources = [target.name] + target.get_source_names()
                if not any(targ <= x for x in sources):
                    return False

        constraints, injections = self._get_relation_data(relation, control)
        self._validate_injection_dict_format(injections)
        assert(constraints is not None)
        assert(injections is not None)
        source_data, target_data = control.extra, target.extra

        # Check constraints match

        for targ_k,source_k in constraints.items():
            if source_k not in source_data:
                continue
            if (targ_v:=target_data.get(targ_k, None)) != (source_v:=source_data[source_k]):
                logging.debug("Constraint does not match: %s(%s) : %s(%s)", targ_k, targ_v, source_k, source_v)
                return False

        target_keys, source_keys = self._get_sum_injection_keys(injections)
        # Check injections. keys must be available, but not necessarily the same
        if bool(source_keys - source_data.keys()):
            logging.debug("source key/data mismatch")
            return False
        if bool(target_keys - target_data.keys()):
            # target don't match
            logging.debug("target  key/data mismatch")
            return False

        return True

    def _get_relation_data(self, relation:Maybe[RelationSpec], control:TaskSpec) -> tuple[Data, Data]:
        """ Extract the relevant relation constraints and injections  """
        match relation:
            case None:
                constraint_d = True
                inject_d     = {}
            case RelationSpec(constraints=constraint_d, inject=inject_d):
                pass

        match constraint_d:
            case False:
                constraint_d = {}
            case True:
                constraint_d = {x:x for x in control.extra.keys()}
            case [*xs]:
                constraint_d = { x:x for x in xs }
            case dict() | TomlGuard():
                pass

        match inject_d:
            case None:
                inject_d = {}
            case [*xs]:
                inject_d = { x:x for x in xs }
            case str() as key_s:
                key      = DKey(key_s, check=dict|TomlGuard, implicit=True)
                inject_d = key(control)
            case dict() | TomlGuard():
                pass

        assert(isinstance(constraint_d, dict))
        assert(isinstance(inject_d, dict))
        return constraint_d, inject_d

    def _get_sum_injection_keys(self, injections) -> tuple[set[str], set[str]]:
        """ Get the target : source keys for injection"""
        source_keys, target_keys= set(), set()
        for k,y in injections.items():
            match y:
                case [*xs]:
                    source_keys.update(xs)
                    target_keys.update(xs)
                case dict():
                    source_keys.update(y.values())
                    target_keys.update(y.keys())

        return target_keys, source_keys

    def match_edge(self, rel:RelationSpec, edges:list[TaskName], *, exclude:None|list=None) -> bool:
        """ Given a list of existing edges,
          return true if any of them are an instantiated version of
          this relations target.

          Return False if this relation has constraints.
          """
        if bool(rel.constraints) or bool(rel.inject):
            return False

        exclude = exclude or []
        for x in edges:
            if x in exclude:
                continue
            if rel.target < x:
                return True

        return False
