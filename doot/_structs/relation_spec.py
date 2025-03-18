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
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from pydantic import (BaseModel, Field, field_validator,
                      model_validator)
from jgdv import Maybe
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.strang import CodeReference, Strang
from jgdv.structs.locator import Location
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import Buildable_p, ProtocolModelMeta
from doot._structs.artifact import TaskArtifact
from doot._structs.task_name import TaskName

# ##-- end 1st party imports

# ##-- types
# isort: off
if TYPE_CHECKING:
   from jgdv import Maybe
   type RelationTarget = TaskName|TaskArtifact
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

INJECT_KEYS : Final[list[str]] = doot.constants.misc.INJECT_KEYS

class RelationMeta_e(enum.Enum):
    """
      What types+synonyms of task relation there can be,
      in the form Obj {rel} Y,

      eg: cake dependsOn baking.
      or: baking requirementFor cake.
      or: eatingCake conflictsWith givingCake
    """
    needs            = enum.auto()
    blocks           = enum.auto()
    # excludes         = enum.auto()

    default          = needs

class RelationSpec(BaseModel, Buildable_p, arbitrary_types_allowed=True, metaclass=ProtocolModelMeta):
    """ {object} is {relation} to {target}

    Object is optional, to allow multiple different objects to have the same relationship to the target.
     Encodes a relation between a object , (who owns this relationspec)
      and the subject of the relation (who is contained within the relation)

      eg: baking dependsOn      mixing. relation=dependsOn, target=mixing.
          baking produces       cake.   r=produces, t=cake.
          baking requirementFor party.  r=requirementFor, t=party.

      May carry additional information:
      - constraints : a list of keys that much match between the task specs of the two tasks
      - inject      : a mapping of { obj.key : sub.key } that will be injected into the object
      - object      : the owning base object of the relationship

    """

    # What the Relation end point is:
    mark_e        : ClassVar[enum] = RelationMeta_e

    target        : TaskName|TaskArtifact
    relation      : RelationMeta_e                                   = RelationMeta_e.needs
    # constraints on spec field equality
    object        : Maybe[TaskName|TaskArtifact]                     = None
    constraints   : bool|list|dict[str, str]                         = False
    inject        : Maybe[str|dict]                                  = None
    _meta         : dict()                                           = {} # Misc metadata

    @classmethod
    def build(cls, data:RelationSpec|ChainGuard|dict|TaskName|str, *, relation:Maybe[RelationSpec.mark_e]=None) -> RelationSpec:
        relation = relation or cls.mark_e.needs
        result = None
        match data:
            case RelationSpec():
                result = data
            case pl.Path():
                result = cls(target=TaskArtifact(data), relation=relation)
            case TaskName() | TaskArtifact():
                result = cls(target=data, relation=relation)
            case str() as x if TaskArtifact._separator in x:
                target = TaskArtifact(x)
                result = cls(target=target, relation=relation)
            case str() as x if Location._separator in x:
                result = Location(x)
                return cls(target=target, relation=relation)
            case str() as x if TaskName._separator in x:
                target = TaskName(x)
                result = cls(target=target, relation=relation)
            case {"path":path} if "task" not in data:
                return cls(target=TaskArtifact(path), relation=relation)
            case {"task": taskname}:
                constraints = data.get("constraints", None) or data.get("constraints_", False)
                inject      = data.get("inject", None)      or data.get("inject_", None)
                result = cls(target=TaskName(taskname), constraints=constraints, inject=inject, relation=relation)
            case _:
                raise ValueError("Bad data used for relation spec", type(data), data)

        return result

    @field_validator("target", mode="before")
    def _validate_target(cls, val) -> RelationTarget:
        match val:
            case TaskName() | TaskArtifact():
                return val
            case pl.Path():
                return TaskArtifact(val)
            case str() if TaskName._separator in val:
                return TaskName(val)
            case _:
                raise ValueError("Unparsable target str")

    @field_validator("constraints", mode="before")
    def _validate_constraints(cls, val) -> bool|dict:
         match val:
             case bool():
                 return val
             case list():
                 return {x:x for x in val}
             case dict():
                 return val
             case _:
                 raise TypeError("Unknown constraints type", val)

    @field_validator("inject", mode="before")
    def _validate_inject(cls, val) -> Maybe[str|dict]:
        match val:
            case None:
                return None
            case str():
                return val
            case ChainGuard() | dict() if all(k in INJECT_KEYS for k in val.keys()):
                return val
            case _:
                raise TypeError("Unknown injection type", val)

    def __str__(self):
        return f"<? {self.relation.name} {self.target}>"

    def __repr__(self):
        return f"<RelationSpec: ? {self.relation.name} {self.target}>"

    def __contains__(self, query:Location.gmark_e|TaskName) -> bool:
        match self.target, query:
            case TaskName(), TaskName():
                return query in self.target
            case TaskArtifact(), Location.gmark_e():
                return query in self.target
            case _, _:
                raise NotImplementedError(self.target, query)

    def to_ordered_pair(self, obj:RelationTarget, *, target:Maybe[TaskName]=None) -> tuple[RelationTarget, RelationTarget]:
        """ a helper to make an edge for the tracker.
          uses the current (abstract) target, unless an instance is provided
          """
        logging.info("Relation to edge: (object:%s) (rel:%s) (target:%s) (target instance:%s)", obj, self.relation, self.target, target)
        match self.relation:
            case RelationMeta_e.needs:
                # target is a predecessor
                return (target or self.target, obj)
            case RelationMeta_e.blocks:
                # target is a succcessor
                return (obj, target or self.target)

    def instantiate(self, *, object:Maybe[RelationTarget]=None, target:Maybe[RelationTarget]=None):
        """
          Duplicate this relation, but with a suitable concrete task or artifact as the object or subject
        """
        match self.target, target:
            case _, None:
                pass
            case TaskName(), TaskArtifact():
                raise doot.errors.TrackingError("tried to instantiate a relation with the wrong target", self.target, target)
            case TaskArtifact(), TaskName():
                raise doot.errors.TrackingError("tried to instantiate a relation with the wrong target", self.target, target)
            case TaskName(), TaskName() if not target.is_uniq():
                raise doot.errors.TrackingError("tried to instantiate a relation with the wrong target status", self.target, target)
            case TaskArtifact(), TaskArtifact() if (match:=self.target.reify(target)) is not None:
                target = match
            case _, _:
                pass

        if target is None:
            target = self.target
        if object is None:
            object = self.object

        return RelationSpec(target=target,
                            object=object or self.object,
                            relation=self.relation,
                            constraints=self.constraints)

    def forward_dir_p(self) -> bool:
        " is this relation's direction obj -> target? "
        return self.relation is RelationMeta_e.blocks
