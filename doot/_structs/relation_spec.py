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
from doot._abstract.protocols import SpecStruct_p
from doot._structs.artifact import DootTaskArtifact
from doot._structs.code_ref import DootCodeReference
from doot._structs.task_name import DootTaskName
from doot.enums import RelationMeta

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class RelationSpec(BaseModel):
    """
    The main encoding for dependencies and dependents.
    A declaration that a TaskName, Artifact is a dependency,
      with any associated metadata.

    in the sentence {X} {relation} {Y},
      this spec encodes {Y} and {relation}.

    {X} is the TaskSpec which holds this relation,
      and so is implicit.

      eg: baking dependsOn      mixing. relation=dependsOn, target=mixing.
          baking produces       cake.   r=produces, t=cake.
          baking requirementFor party.  r=requirementFor, t=party.

    """

    # What the Relation end point is:
    target        : DootTaskName|DootTaskArtifact
    relation      : RelationMeta        = RelationMeta.dependsOn
    constraints   : None|list[str]      = None # constraints on spec field matches
    _meta         : dict()              = {} # Misc metadata

    @staticmethod
    def build(data:RelationSpec|TomlGuard|dict|DootTaskName|str, *, relation:None|RelationMeta=None) -> RelationSpec:
        relation = relation or RelationMeta.default
        match data:
            case RelationSpec():
                return data
            case DootTaskName() | DootTaskArtifact():
                return RelationSpec(target=data, relation=relation)
            case {"loc": str()|pl.Path()}:
                return RelationSpec(target=DootTaskArtifact.build(data), relation=relation)
            case {"file": str()|pl.Path() as x}:
                return RelationSpec(target=DootTaskArtifact.build(data), relation=relation)
            case {"task": taskname }:
                keys = data.get("keys", None)
                return RelationSpec(target=taskname, constraints=keys, relation=relation)
            case str() | pl.Path():
                return RelationSpec(target=data, relation=relation)
            case _:
                raise ValueError("Bad data used for relation spec", data)

    @field_validator("target", mode="before")
    def _validate_target(cls, val) -> DootTaskName|DootTaskArtifact:
        match val:
            case DootTaskName() | DootTaskArtifact():
                return val
            case pl.Path():
                return DootTaskArtifact.build(val)
            case str() if val.startswith(DootTaskArtifact._toml_str_prefix):
                return DootTaskArtifact.build(val)
            case str() if DootTaskName._separator in val:
                return DootTaskName.build(val)
            case _:
                raise ValueError("Unparsable target str")


    def __str__(self):
        return f"<? {self.relation.name}> {self.target}"
    def __contains__(self, query:TaskFlags|LocationMeta) -> bool:
        match self.target, query:
             case DootTaskName(), TaskFlags():
                 return query in self.target
             case DootTaskArtifact(), LocationMeta():
                 return query in self.target

    def to_edge(self, other:DootTaskName|DootTaskArtifact, *, instance:None|DootTaskName=None) -> tuple[DootTaskName|DootTaskArtifact, DootTaskName|DootTaskArtifact]:
        """ a helper to make an edge for the tracker.
          uses the current target, unless an instance is provided
          """
        logging.info("Relation to edge: (rel:%s) (target:%s) (other:%s) (instance:%s)", self.relation, self.target, other, instance)
        match self.relation:
            case RelationMeta.dep:
                return (instance or self.target, other)
            case RelationMeta.req:
                return (other, instance or self.target)

    def match_simple_edge(self, edges:list[DootTaskName]) -> bool:
        """ Given a list of existing edges,
          return true if any of them are an instantiated version of
          this relations target.

          Return False if this relation has constraints.
          """
        if not bool(self.constraints):
            return False
        for x in edges:
            if self.target < x:
                return True

        return False

    def invert(self, source) -> RelationSpec:
        """ Instead of X depends on Y,
          get Y required for X
        """
        match self.relation:
            case RelationMeta.dep:
                relation = RelationMeta.req
            case _:
                relation = RelationMeta.dep

        return RelationSpec(target=source, constraints=self.constraints, relation=relation)

    def instantiate(self, target:DootTaskName|DootTaskArtifact):
        """
          Duplicate this relation, but with a suitable concrete task or artifact
        """
        match self.target, target:
            case DootTaskName(), DootTaskArtifact():
                raise doot.errors.DootTaskTrackingError("tried to instantiate a relation with the wrong target", self.target, target)
            case DootTaskArtifact(), DootTaskName():
                raise doot.errors.DootTaskTrackingError("tried to instantiate a relation with the wrong target", self.target, target)
            case DootTaskName(), DootTaskName() if TaskFlags.CONCRETE in self.target or TaskFlags.CONCRETE not in target:
                raise doot.errors.DootTaskTrackingError("tried to instantiate a relation with the wrong target status", self.target, target)
            case DootTaskName(), DootTaskName() if LocationMeta.abstract not in self.target or LocationMeta.abstract in target:
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
