#!/usr/bin/env python3
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
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import Buildable_p, ProtocolModelMeta
from doot._structs.artifact import TaskArtifact
from doot._structs.code_ref import CodeReference
from doot._structs.task_name import TaskName
from doot.enums import RelationMeta_e

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class RelationSpec(BaseModel, Buildable_p, metaclass=ProtocolModelMeta):
    """ ? is {self.relation} to {self.target}

     Encodes a relation between an implicit subject, (who owns this relationspec)
      and the object of the relation (who is contained within the relationspec)

      eg: baking dependsOn      mixing. relation=dependsOn, target=mixing.
          baking produces       cake.   r=produces, t=cake.
          baking requirementFor party.  r=requirementFor, t=party.


      May carry additional information:
      - constraints : a list of keys that much match between the task specs of the two tasks
      - injections  : a mapping of { obj.key : sub.key } that will be injected into the object

      NOTE: injections *do not* do expansion, they will just copy the value, allowing expansion to occur later.
      So: injection={'a': '{taskkey}/b'} won't work, but {'a':'{taskkey}/b', 'taskkey':'taskkey'} will.
      Or: injection={'a': '{otherkey}/b', 'otherkey':'taskkey'}
    """

    # What the Relation end point is:
    target        : TaskName|TaskArtifact
    relation      : RelationMeta_e             = RelationMeta_e.dependsOn
    constraints   : None|list[str]           = None # constraints on spec field matches
    injections    : None|dict                = None
    _meta         : dict()                   = {} # Misc metadata

    @staticmethod
    def build(data:RelationSpec|TomlGuard|dict|TaskName|str, *, relation:None|RelationMeta_e=None) -> RelationSpec:
        relation = relation or RelationMeta_e.default
        match data:
            case RelationSpec():
                return data
            case TaskName() | TaskArtifact():
                return RelationSpec(target=data, relation=relation)
            case {"loc": str()|pl.Path()}:
                return RelationSpec(target=TaskArtifact.build(data), relation=relation)
            case {"file": str()|pl.Path() as x}:
                return RelationSpec(target=TaskArtifact.build(data), relation=relation)
            case {"task": taskname}:
                constraints = data.get("constraints", None)
                injections  = data.get("injections" , None)
                return RelationSpec(target=taskname, constraints=constraints, injections=injections, relation=relation)
            case str() | pl.Path():
                return RelationSpec(target=data, relation=relation)
            case _:
                raise ValueError("Bad data used for relation spec", data)

    @field_validator("target", mode="before")
    def _validate_target(cls, val) -> TaskName|TaskArtifact:
        match val:
            case TaskName() | TaskArtifact():
                return val
            case pl.Path():
                return TaskArtifact.build(val)
            case str() if val.startswith(TaskArtifact._toml_str_prefix):
                return TaskArtifact.build(val)
            case str() if TaskName._separator in val:
                return TaskName.build(val)
            case _:
                raise ValueError("Unparsable target str")


    def __str__(self):
        return f"<? {self.relation.name}> {self.target}"
    def __contains__(self, query:TaskMeta_f|LocationMeta_f) -> bool:
        match self.target, query:
             case TaskName(), TaskMeta_f():
                 return query in self.target
             case TaskArtifact(), LocationMeta_f():
                 return query in self.target

    def to_edge(self, other:TaskName|TaskArtifact, *, instance:None|TaskName=None) -> tuple[TaskName|TaskArtifact, TaskName|TaskArtifact]:
        """ a helper to make an edge for the tracker.
          uses the current target, unless an instance is provided
          """
        logging.info("Relation to edge: (rel:%s) (target:%s) (other:%s) (instance:%s)", self.relation, self.target, other, instance)
        match self.relation:
            case RelationMeta_e.dep:
                return (instance or self.target, other)
            case RelationMeta_e.req:
                return (other, instance or self.target)

    def match_simple_edge(self, edges:list[TaskName], *, exclude:None|list=None) -> bool:
        """ Given a list of existing edges,
          return true if any of them are an instantiated version of
          this relations target.

          Return False if this relation has constraints.
          """
        if bool(self.constraints) or bool(self.injections):
            return False

        exclude = exclude or []
        for x in edges:
            if x in exclude:
                continue
            if self.target < x:
                return True

        return False

    def invert(self, source) -> RelationSpec:
        """ Instead of X depends on Y,
          get Y required for X
        """
        match self.relation:
            case RelationMeta_e.dep:
                relation = RelationMeta_e.req
            case _:
                relation = RelationMeta_e.dep

        return RelationSpec(target=source, constraints=self.constraints, relation=relation)

    def instantiate(self, target:TaskName|TaskArtifact):
        """
          Duplicate this relation, but with a suitable concrete task or artifact
        """
        match self.target, target:
            case TaskName(), TaskArtifact():
                raise doot.errors.DootTaskTrackingError("tried to instantiate a relation with the wrong target", self.target, target)
            case TaskArtifact(), TaskName():
                raise doot.errors.DootTaskTrackingError("tried to instantiate a relation with the wrong target", self.target, target)
            case TaskName(), TaskName() if TaskMeta_f.CONCRETE in self.target or TaskMeta_f.CONCRETE not in target:
                raise doot.errors.DootTaskTrackingError("tried to instantiate a relation with the wrong target status", self.target, target)
            case TaskName(), TaskName() if LocationMeta_f.abstract not in self.target or LocationMeta_f.abstract in target:
                raise doot.errors.DootTaskTrackingError("tried to instantiate a relation with the wrong target status", self.target, target)
            case _, _:
                pass

        match self.target.match_with(target):
            case None:
                logging.debug("Couldn't match %s onto %s", target, self.target)
                return self
            case result:
                return RelationSpec(target=result,
                                    relation=self.relation,
                                    constraints=self.constraints)

    def forward_dir_p(self) -> bool:
        " is this relation's direction predecessor -> successor? "
        return self.relation is RelationMeta_e.req
