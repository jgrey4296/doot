#!/usr/bin/env python3
"""



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

# ##-- 3rd party imports
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot._structs.relation_spec import RelationSpec
from doot.structs import DKey, TaskSpec

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class TaskMatcher_m:
    """ Match Tasks/Specs with constraints """

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
        assert(constraints is not None)
        assert(injections is not None)
        target_keys, source_keys = self._get_sum_injection_keys(injections)
        source_data, target_data = control.extra, target.extra

        # Check constraints match
        match injections.get('suffix', None):
            case None:
                pass
            case str() as suffix if suffix not in target.name:
                logging.debug("Suffix %s not found in %s", suffix, target.name)
                return False

        for targ_k,source_k in constraints.items():
            if source_k not in source_data:
                continue
            if (targ_v:=target_data.get(targ_k, None)) != (source_v:=source_data[source_k]):
                logging.debug("Constraint does not match: %s(%s) : %s(%s)", targ_k, targ_v, source_k, source_v)
                return False

        target_keys, source_keys = self._get_sum_injection_keys(injections)
        # Check injections. keys must be available, but not necessarily the same
        if bool(source_keys - source_data.keys()):
            logging.debug("source key/data mismatch: %s", source_keys - source_data.keys())
            return False
        if bool(target_keys - target_data.keys()):
            # target don't match
            logging.debug("target key/data mismatch: %s", target_keys - target_data.keys())
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
            case dict() | ChainGuard():
                pass

        match inject_d:
            case None:
                inject_d = {}
            case [*xs]:
                inject_d = { x:x for x in xs }
            case str() as key_s:
                key      = DKey(key_s, check=dict|ChainGuard, implicit=True)
                inject_d = key(control)
            case dict() | ChainGuard():
                pass

        assert(isinstance(constraint_d, dict))
        assert(isinstance(inject_d, dict))
        return constraint_d, inject_d

    def _get_sum_injection_keys(self, injections) -> tuple[set[str], set[str]]:
        """ Get the target : source keys for injection """
        source_keys, target_keys= set(), set()
        for k,y in injections.items():
            match y:
                case [*xs]:
                    source_keys.update(xs)
                    target_keys.update(xs)
                case dict():
                    source_keys.update({y2 for y2 in y.values() if isinstance(y2, DKey)})
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
