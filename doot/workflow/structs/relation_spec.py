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
from jgdv.structs.strang._interface import StrangMarkAbstract_e
from jgdv.structs.locator import Location
from jgdv._abstract.protocols import Buildable_p
from jgdv._abstract.pydantic_proto import ProtocolModelMeta
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors

# ##-- end 1st party imports

from .._interface import RelationMeta_e, Task_p
from .task_name import TaskName
from .artifact import  TaskArtifact
from .inject_spec import InjectSpec

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


class RelationSpec(BaseModel, Buildable_p, arbitrary_types_allowed=True, metaclass=ProtocolModelMeta):
    """ {object} is {relation} to {target}

    Object is optional, to allow multiple different objects to have the same relationship to the target.
    Encodes a relation between an object , (who owns this relationspec)
    and the subject of the relation (who is contained within the relation)

    eg: (baking <needs> mixing)
        (baking <blocks> cake)

    May carry additional information:
    - constraints : dict|list. Maps obj[x] == targ[y] requirements
    - inject      : InjectSpec. Maps targ[x] = obj[y] values to pass to target.
    - object      : Maybe[TaskName]. the owning base object of the relationship

    """

    # What the Relation end point is:
    Marks        : ClassVar[enum]  = RelationMeta_e
    ##--|
    target       : TaskName|TaskArtifact
    relation     : RelationMeta_e                = RelationMeta_e.needs
    object       : Maybe[TaskName|TaskArtifact]  = None
    constraints  : dict[str, str]                = {}
    inject       : Maybe[InjectSpec]             = None
    _meta        : dict()                        = {} # Misc metadata

    @classmethod
    def build(cls, data:RelationSpec|ChainGuard|dict|TaskName|str, *, relation:Maybe[RelationSpec.Marks]=None) -> RelationSpec:
        """ Create a new relation, defaulting to a requirement.

        """
        relation = relation or cls.Marks.needs
        result = None
        match data:
            case RelationSpec(): # Do Nothing
                result = data
            case pl.Path(): # Rely on a file
                result = cls(target=TaskArtifact(data), relation=relation)
            case TaskName() | TaskArtifact():
                result = cls(target=data, relation=relation)
            case str() as x if TaskArtifact.section(0).end in x:
                target = TaskArtifact(x)
                result = cls(target=target, relation=relation)
            case str() as x if Location.section(0).end in x:
                result = Location(x)
                return cls(target=target, relation=relation)
            case str() as x if TaskName.section(0).end in x:
                target = TaskName(x)
                result = cls(target=target, relation=relation)
            case {"path":path} if "task" not in data:
                return cls(target=TaskArtifact(path), relation=relation)
            case {"task": taskname}:
                constraints = data.get("constraints", None) or data.get("constraints_", [])
                inject      = data.get("inject", None)      or data.get("inject_", None)
                result      = cls(target=TaskName(taskname),
                                  constraints=constraints,
                                  inject=inject,
                                  relation=relation)
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
            case str() if TaskName.section(0).end in val:
                return TaskName(val)
            case _:
                raise ValueError("Unparsable target str")

    @field_validator("constraints", mode="before")
    def _validate_constraints(cls, val) -> dict:
         match val:
             case list():
                 return {x:x for x in val}
             case dict():
                 return val
             case _:
                 raise TypeError("Unknown constraints type", val)

    @field_validator("inject", mode="before")
    def _validate_inject(cls, val) -> Maybe[str|InjectSpec]:
        match val:
            case None:
                return None
            case str():
                return val
            case dict() | ChainGuard():
                return InjectSpec.build(val)
            case _:
                raise TypeError("Unknown injection type", val)

    def __str__(self):
        return f"<? {self.relation.name} {self.target}>"

    def __repr__(self):
        return f"<RelationSpec: ? {self.relation.name} {self.target}>"

    def __contains__(self, query:StrangMarkAbstract_e|TaskName|TaskArtifact) -> bool:
        match self.target, query:
            case TaskName(), TaskName():
                return query <= self.target
            case TaskArtifact(), TaskArtifact():
                return query in self.target
            case TaskArtifact(), StrangMarkAbstract_e():
                return query in self.target
            case _, _:
                raise NotImplementedError(self.target, query)

    def to_ordered_pair(self, obj:RelationTarget, *, target:Maybe[TaskName]=None) -> tuple[RelationTarget, RelationTarget]:
        """ a helper to make an edge for the tracker.
          uses the current (abstract) target, unless an instance is provided
          """
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
            case TaskName(), TaskName() if not target.uuid():
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
        """ is this relation's direction obj -> target? """
        return self.relation is RelationMeta_e.blocks


    def accepts(self, control:Task_p|TaskSpec, target:Task_p|TaskSpec) -> bool:
        """ Test if this pair of Tasks satisfies the relation """
        if not (target.name.uuid() and control.name.uuid()):
            # abstract specs can't satisfy a relation
            return False
        if not (self.target < target.name):
            # targets that are not extensions of the target don't satisfy
            return False

        control_vals = control.state if isinstance(control, Task_p) else control.extra
        target_vals  = target.state  if isinstance(target, Task_p) else target.extra

        # Check constraints match
        for targ_k,source_k in self.constraints.items():
            if source_k not in control_vals:
                continue
            if targ_k not in target_vals:
                return False

            if (targ_v:=target_vals.get(targ_k, None)) != (source_v:=control_vals[source_k]):
                logging.debug("[Relation] Constraint does not match: %s(%s) : %s(%s)", targ_k, targ_v, source_k, source_v)
                return False
        else:
            pass

        if self.inject is None:
            return True

        return self.inject.validate(control, target)
