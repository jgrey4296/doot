#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

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
from dataclasses import InitVar, dataclass, field, _MISSING_TYPE
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping, Self,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from pydantic import BaseModel, Field, model_validator, field_validator, BeforeValidator, WrapValidator, ValidationInfo, ValidatorFunctionWrapHandler
from typing_extensions import Annotated
from dataclasses import fields
import importlib
from importlib.metadata import EntryPoint
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.enums import TaskFlags, ReportEnum, TaskQueueMeta, RelationMeta
from doot._structs.task_name import DootTaskName
from doot._structs.code_ref import DootCodeReference
from doot._structs.action_spec import DootActionSpec
from doot._structs.artifact import DootTaskArtifact
from doot._abstract.structs import SpecStruct_p
from doot._abstract.task import Task_i
from doot._structs.relation_spec import RelationSpec

def _prepare_action_group(deps:list[str], handler:ValidatorFunctionWrapHandler, info:ValidationInfo) -> list[RelationSpec|DootActionSpec]:
    """
      Prepares action groups / dependencies,
      converting toml specified strings, list, and dicts to Artifacts (ie:files), Task Names, ActionSpecs

      As a wrap handler, it has the context of what field is being processed,
      this allows it to set the correct RelationMeta type

      # TODO handle callables?
    """
    results = []
    if deps is None:
        return results

    relation_type = RelationMeta.dependsOn if info.field_name not in DootTaskSpec._dependant_groups else RelationMeta.dependantOf
    for x in deps:
        match x:
            case DootActionSpec() | RelationSpec():
                results.append(x)
            case { "do": action  }:
                results.append(DootActionSpec.build(x))
            case _:
                results.append(RelationSpec.build(x, relation=relation_type))

    return handler(results)


ActionGroup = Annotated[list[DootActionSpec|RelationSpec], WrapValidator(_prepare_action_group)]

class DootTaskSpec(BaseModel, arbitrary_types_allowed=True, extra="allow"):
    """ The information needed to describe a generic task.
    Optional things are shoved into 'extra', so things can use .on_fail on the tomlguard

    the cli parser can understand cli=[{}] specs
    actions                      : list[ [args] | {do="", args=[], **kwargs} ]

    """
    name                         : str|DootTaskName
    doc                          : list[str]                                                               = []
    source                       : DootTaskName|pl.Path|None                                               = None

    # Action Groups:
    actions                      : ActionGroup                                                             = []
    required_for                 : ActionGroup                                                             = []
    depends_on                   : ActionGroup                                                             = []
    setup                        : ActionGroup                                                             = []
    cleanup                      : ActionGroup                                                             = []
    on_fail                      : ActionGroup                                                             = []

    # Any additional information:
    version                      : str                                                                     = doot.__version__ # TODO: make dict?
    priority                     : int                                                                     = 10
    ctor                         : DootCodeReference                                                       = Field(default=None, validate_default=True)
    queue_behaviour              : TaskQueueMeta                                                           = TaskQueueMeta.default
    print_levels                 : TomlGuard                                                               = Field(default_factory=TomlGuard)
    flags                        : TaskFlags                                                               = TaskFlags.default
    # task specific extras to use in state
    _default_ctor         : ClassVar[str]       = doot.constants.entrypoints.DEFAULT_TASK_CTOR_ALIAS
    _allowed_print_locs   : ClassVar[list[str]] = doot.constants.printer.PRINT_LOCATIONS
    _allowed_print_levels : ClassVar[list[str]] = ["INFO", "WARNING", "DEBUG", "EXCEPTION"]
    _action_group_wipe    : ClassVar[dict]      = {"required_for": [], "setup": [], "actions": [], "depends_on": []}
    # Action Groups that are dependant on, rather than are dependencies of, the task:
    _dependant_groups    : ClassVar[list[str]]  = ["required_for", "cleanup", "on_fail"]

    @staticmethod
    def build(data:TomlGuard|dict|DootTaskName|str) -> Self:
        match data:
            case TomlGuard() | dict():
                return DootTaskSpec.model_validate(data)
            case DootTaskName():
                return DootTaskSpec(name=data)
            case str():
                return DootTaskSpec(name=DootTaskName.build(data))

    @model_validator(mode="before")
    def _convert_toml_keys(cls, data:dict) -> dict:
        """ converts a-key into a_key, and joins group+name """
        cleaned = {k.replace("-","_") : v  for k,v in data.items()}
        if "group" in cleaned and DootTaskName._separator not in cleaned["name"]:
            cleaned['name'] = DootTaskName._separator.join([cleaned['group'], cleaned['name']])
            del cleaned['group']
        return cleaned

    @model_validator(mode="after")
    def _validate_metadata(self):
        self.flags |= self.name.meta
        if self.extra.on_fail(False).disabled():
            self.flags |= TaskFlags.DISABLED
        try:
            match self.ctor.try_import():
                case x if issubclass(x, Task_i):
                    self.flags |= x._default_flags
                    self.name.meta |= x._default_flags
                case x:
                    pass
        except ImportError as err:
            logging.warning("Ctor Import Failed for: %s : %s", self.name, self.ctor)
            self.flags |= TaskFlags.DISABLED
            self.ctor = None

        return self

    @field_validator("name", mode="before")
    def _validate_name(cls, val):
        match val:
            case DootTaskName():
                return val
            case str():
                name = DootTaskName.build(val)
                return name
            case _:
                raise TypeError("A DootTaskSpec Name should be a str or DootTaskName", val)

    @field_validator("flags", mode="before")
    def _validate_flags(cls, val):
        match val:
            case TaskFlags():
                return val
            case str()|list():
                return TaskFlags.build(val)

    @field_validator("ctor", mode="before")
    def _validate_ctor(cls, val):
        match val:
            case None:

                default_alias = DootTaskSpec._default_ctor
                coderef_str   = doot.aliases.task[default_alias]
                return DootCodeReference.build(coderef_str)
            case EntryPoint():
                return DootCodeReference.build(val)
            case DootCodeReference():
                return val
            case type()|str():
                return DootCodeReference.build(val)
            case _:
                return DootCodeReference.build(val)

    @field_validator("print_levels", mode="before")
    def _validate_print_levels(cls, val):
        match val:
            case dict() | TomlGuard() if any(x not in DootTaskSpec._allowed_print_locs for x in val.keys()):
                raise ValueError("Print targets must be those declared in doot.constants.printer.PRINT_LOCATIONS", val.keys(), DootTaskSpec._allowed_print_locs)
            case dict() | TomlGuard() if any(x not in DootTaskSpec._allowed_print_levels for x in val.values()):
                raise ValueError("Print levels must be standard logging levels", val.values(), DootTaskSpec._allowed_print_levels)
            case dict():
                return TomlGuard(val)
            case TomlGuard():
                return val
            case None:
                return TomlGuard({})
            case _:
                raise TypeError("print_levels must be a dict or TomlGuard", val)

    @field_validator("queue_behaviour", mode="before")
    def _validate_queue_behaviour(cls, val):
        match val:
            case TaskQueueMeta():
                return val
            case str():
                return TaskQueueMeta.build(val)
            case _:
                raise ValueError("Queue Behaviour needs to be a str or a TaskQueueMeta enum", val)

    @field_validator("source", mode="before")
    def _validate_source(cls, val):
        match val:
            case DootTaskName() | pl.Path | None:
                return val
            case str():
                return DootTaskName.build(val)

    def instantiate_onto(self, data:None|DootTaskSpec) -> DootTaskSpec:
        """ apply self over the top of data """
        match data:
            case None:
                return self.specialize_from(self)
            case DootTaskSpec():
                return data.specialize_from(self)
            case _:
                raise TypeError("Can't instantiate onto something not a task spec", data)

    def specialize_from(self, data:dict|DootTaskSpec) -> DootTaskSpec:
        """
          apply data over the top of self
        """
        match data:
            case DootTaskSpec() if self is data:
                # specializing on self, just instantiate a name
                specialized = dict(self)
                specialized['name']   = data.name.instantiate()
                specialized['source'] = self.name
                return DootTaskSpec.build(specialized)
            case DootTaskSpec(source=DootTaskName() as source) if not source <= self.name:
                raise doot.errors.DootTaskTrackingError("Tried to specialize a task that isn't based on this task", str(data.name), str(self.name), str(data.source))
            case DootTaskSpec(ctor=ctor) if self.ctor != ctor and ctor != DootTaskSpec._default_ctor:
                raise doot.errors.DootTaskTrackingError("Unknown ctor for spec", data.ctor)
            case DootTaskSpec():
                specialized = dict(self)
                specialized.update({k:v for k,v in dict(data).items() if k in data.model_fields_set})
            case dict():
                specialized = dict(self)
                specialized.update(data)
                return DootTaskSpec.build(specialized)

        # Then special updates
        specialized['name']   = data.name.instantiate()
        specialized['source'] = self.name

        specialized['actions']      = self.actions      + data.actions
        specialized["depends_on"]   = self.depends_on   + data.depends_on
        specialized["required_for"] = self.required_for + data.required_for
        specialized["cleanup"]      = self.cleanup      + data.cleanup
        specialized["on_fail"]      = self.on_fail      + data.on_fail
        specialized["setup"]        = self.setup        + data.setup

        specialized['flags']        = self.flags | data.flags

        logging.debug("Specialized Task: %s on top of: %s", data.name.readable, self.name)
        return DootTaskSpec.build(specialized)

    def make(self, ensure=Any) -> Task_i:
        """ Create actual task instance """
        task_ctor = self.ctor.try_import(ensure=ensure)
        return task_ctor(self)

    def __hash__(self):
        return hash(str(self.name))

    @property
    def params(self) -> dict:
        return self.model_extra

    @property
    def extra(self) -> TomlGuard:
        return TomlGuard(self.model_extra)

    @property
    def action_groups(self):
        # TODO: use introspection on the model to get any fields annotated as an ActionGroup
        return [self.depends_on, self.setup, self.actions, self.cleanup, self.on_fail]

    def job_top(self) -> None|DootTaskSpec:
        """
          Generate a top spec for a job, taking the jobs cleanup actions
          and using them as the head's main action.
          Depends on the job, and its reactively queued.
        """
        if TaskFlags.JOB not in self.flags:
            return None
        if TaskFlags.JOB_HEAD in self.flags:
            return None
        if TaskFlags.CONCRETE in self.flags:
            return None
        if self.name.job_head() is self.name:
            return None

        # build $head$
        head : DootTaskSpec = DootTaskSpec.build({
            "name"            : self.name.job_head(),
            "source"          : None,
            "actions"         : self.cleanup,
            "print_levels"    : self.print_levels,
            "extra"           : self.extra,
            "queue_behaviour" : TaskQueueMeta.reactive,
            "depends_on"      : [self.name],
            "flags"           : self.flags | TaskFlags.JOB_HEAD,
            })
        return head

    def match_with_constraints(self, control:DootTaskSpec, *, relation:None|RelationSpec=None) -> bool:
        """ Test this spec to see if it matches a spec,
          when using a given relation and a given controlling spec to source values from

          if not given a relation, acts as a coherence check between
          self(a concrete spec) and control(the abstract source spec)
          """
        match relation:
            case None:
                assert(control.name < self.name)
                constriants = control.extra.keys()
            case RelationSpec(constraints=None):
                return True
            case RelationSpec(constraints=constraints):
                assert(relation.target < self.name)


        extra         = self.extra
        control_extra = control.extra
        for k in constraints:
            if k not in extra:
                return False
            if extra[k] != control_extra[k]:
                return False
        else:
            return True

    def build_relevant_data(self, context:RelationSpec) -> dict:
        """ Builds a dict of the data a matching spec will need, according
          to a relations constraints.
        """
        if not bool(context.constraints):
            return {}
        extra = self.extra
        return {k:extra[k] for k in context.constraints}
