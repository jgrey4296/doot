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
import weakref
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot._structs.relation_spec import RelationSpec
from doot.structs import DKey, TaskSpec, InjectSpec

# ##-- end 1st party imports

from doot._structs import _interface as S_API

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    type Data = dict
##--|

# isort: on
# ##-- end types

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
            case None if not control.name < target.name:
                return False
            case None:
                return True
            case RelationSpec(target=targ):
                # the target instance must be more specific than the target mentioned in the relation
                sources = [target.name] + target.get_source_names()
                if not any(targ <= x for x in sources):
                    return False

        assert(isinstance(relation, RelationSpec))
        match self._matches_constraints(control, relation, target):
            case False:
                return False
            case _:
                pass
        match self._matches_injections(control, relation, target):
            case False:
                return False
            case _:
                pass

        return True

    def _matches_constraints(self, parent:TaskSpec, relation:RelationSpec, child:TaskSpec) -> bool:
        match relation:
            case RelationSpec(constraints=constraints) if bool(constraints):
                pass
            case _:
                return True

        # Check constraints match
        for targ_k,source_k in constraints.items():
            if source_k not in parent.extra:
                continue
            if (targ_v:=child.extra.get(targ_k, None)) != (source_v:=parent.extra[source_k]):
                logging.debug("Constraint does not match: %s(%s) : %s(%s)", targ_k, targ_v, source_k, source_v)
                return False

        else:
            return True

    def _matches_injections(self, parent:TaskSpec, relation:RelationSpec, child:TaskSpec) -> bool:
        match relation:
            case RelationSpec(inject=InjectSpec() as inject) if bool(inject):
                pass
            case _:
                return True

        needed = child.extra.on_fail([])[S_API.MUST_INJECT_K]()
        match inject.validate_against(source=parent.extra.keys(), target=child.extra.keys(), needed=needed):
            case [surplus, missing]:
                return False
            case _:
                return True

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
