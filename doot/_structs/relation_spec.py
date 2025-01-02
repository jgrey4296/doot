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
from jgdv.structs.strang.location import Location
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import Buildable_p, ProtocolModelMeta
from doot._structs.artifact import TaskArtifact
from doot._structs.task_name import TaskName

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

type RelationTarget = TaskName|TaskArtifact

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

      NOTE: inject *do not* do expansion, they will just copy the value, allowing expansion to occur later.
      So: injection={'a': '{taskkey}/b'} won't work, but {'a':'{taskkey}/b', 'taskkey':'taskkey'} will.
      Or: injection={'a': '{otherkey}/b', 'otherkey':'taskkey'}
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

    @staticmethod
    def build(data:RelationSpec|ChainGuard|dict|TaskName|str, *, relation:Maybe[RelationSpec.mark_e]=None) -> RelationSpec:
        relation = relation or RelationSpec.mark_e.needs
        match data:
            case RelationSpec():
                return data
            case pl.Path():
                return RelationSpec(target=TaskArtifact(data), relation=relation)
            case TaskName() | TaskArtifact():
                return RelationSpec(target=data, relation=relation)
            case str():
                try:
                    data = TaskArtifact(data)
                except (ValueError, KeyError):
                    data = TaskName(data)
                return RelationSpec(target=data, relation=relation)
            case {"path":path} if "task" not in data:
                return RelationSpec(target=TaskArtifact(path), relation=relation)
            case {"task": taskname}:
                constraints = data.get("constraints", None) or data.get("constraints_", False)
                inject      = data.get("inject", None)      or data.get("inject_", None)
                return RelationSpec(target=taskname, constraints=constraints, inject=inject, relation=relation)
            case _:
                raise ValueError("Bad data used for relation spec", data)

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
    def _validate_constraints(cls, val):
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
    def _validate_inject(cls, val):
        match val:
            case None:
                return None
            case str():
                return val
            case ChainGuard() | dict() if all(k in ["now","delay", "insert"] for k in val.keys()):
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
