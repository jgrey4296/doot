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
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
from dataclasses import _MISSING_TYPE, InitVar, dataclass, field, fields
from importlib.metadata import EntryPoint
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Literal, Mapping, Match,
                    MutableMapping, Protocol, Self, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from pydantic import (BaseModel, BeforeValidator, Field, ValidationError,
                      ValidationInfo, ValidatorFunctionWrapHandler,
                      WrapValidator, field_validator, model_validator)
from tomlguard import TomlGuard
from typing_extensions import Annotated

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import SpecStruct_p
from doot._abstract.task import Task_i
from doot._structs.action_spec import ActionSpec
from doot._structs.artifact import TaskArtifact
from doot._structs.code_ref import CodeReference
from doot._structs.relation_spec import RelationSpec
from doot._structs.task_name import TaskName
from doot.enums import (LocationMeta, RelationMeta, ReportEnum, TaskFlags,
                        TaskQueueMeta)

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

def _prepare_action_group(deps:list[str], handler:ValidatorFunctionWrapHandler, info:ValidationInfo) -> list[RelationSpec|ActionSpec]:
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

    relation_type = RelationMeta.requirementFor if info.field_name in TaskSpec._dependant_groups else RelationMeta.dependencyOf
    for x in deps:
        match x:
            case ActionSpec() | RelationSpec():
                results.append(x)
            case { "do": action  }:
                results.append(ActionSpec.build(x))
            case _:
                results.append(RelationSpec.build(x, relation=relation_type))

    return handler(results)

ActionGroup = Annotated[list[ActionSpec|RelationSpec], WrapValidator(_prepare_action_group)]

class _SpecUtils_m:

    def instantiate_onto(self, data:None|TaskSpec) -> TaskSpec:
        """ apply self over the top of data """
        match data:
            case None:
                return self.specialize_from(self)
            case TaskSpec():
                return data.specialize_from(self)
            case _:
                raise TypeError("Can't instantiate onto something not a task spec", data)

    def instantiate_transformer(self, target:TaskArtifact|tuple[TaskArtifact, TaskArtifact]) -> None|TaskSpec:
        """ Create an instantiated transformer spec.
          ie     : ?.txt -> spec -> ?.blah
          becomes: a.txt -> spec -> a.blah

          can be given one artifact, which will be used for matching on pre and post,
          or a tuple, which specifies an exact transform

          TODO: handle ?/?.txt, */?.txt, blah/*/?.txt, path/blah.?
        """
        match target:
            case TaskArtifact():
                pre, post = target, target
            case (TaskArtifact() as pre, TaskArtifact() as post):
                pass

        instance = self.instantiate_onto(None)
        match self.transformer_of():
            case None:
                raise doot.errors.DootTaskTrackingError("Tried to transformer instantiate a non-transformer", self.name)
            case (x, y) if pre in x.target or post in y.target:
                # exact transform
                # replace x with pre in depends_on
                instance.depends_on.remove(x)
                instance.depends_on.append(x.instantiate(pre))
                # replace y with post in required_for
                instance.required_for.remove(y)
                instance.required_for.append(y.instantiate(post))
            case _:
                return None

        return instance

    def make(self, ensure:type=Any) -> Task_i:
        """ Create actual task instance """
        task_ctor = self.ctor.try_import(ensure=ensure)
        return task_ctor(self)

    def job_top(self) -> list[TaskSpec]:
        """
          Generate a top spec for a job, taking the jobs cleanup actions
          and using them as the head's main action.
          Cleanup relations are turning into the head's dependencies
          Depends on the job, and its reactively queued.

          Returns a list to allow for sequencing:
          ie: job -> [subtasks] -> job_head -> [cleanup dependencies] -> job cleanup

        """
        tasks = []
        if TaskFlags.JOB not in self.flags:
            return tasks
        if (TaskFlags.CONCRETE | TaskFlags.JOB_HEAD) & self.flags:
            return tasks
        if self.name.job_head() == self.name:
            return tasks

        # build $head$
        head : TaskSpec = TaskSpec.build({
            "name"            : self.name.job_head(),
            "sources"         : self.sources[:] + [self.name, None],
            "extra"           : self.extra,
            "queue_behaviour" : TaskQueueMeta.reactive,
            "depends_on"      : [self.name],
            "required_for"    : [self.name.job_head().subtask("cleanup")] if bool(self.cleanup) else [],
            "flags"           : (self.flags | TaskFlags.JOB_HEAD) & ~TaskFlags.JOB,
            })
        assert(TaskFlags.JOB not in head.name)
        assert(TaskFlags.JOB not in head.flags)
        tasks.append(head)
        if not bool(self.cleanup):
            return tasks

        cleanup : TaskSpec = TaskSpec.build({
            "name"            : self.name.job_head().subtask("cleanup"),
            "sources"         : self.sources[:] + [self.name, None],
            "actions"         : [x for x in self.cleanup if isinstance(x, ActionSpec)],
            "extra"           : self.extra,
            "queue_behaviour" : TaskQueueMeta.reactive,
            "depends_on"      : [self.name, self.name.job_head()] + [x for x in self.cleanup if isinstance(x, RelationSpec)],
            "flags"           : (self.flags | TaskFlags.TASK) & ~TaskFlags.JOB,
            })
        tasks.append(cleanup)
        return tasks

    def match_with_constraints(self, control:TaskSpec, *, relation:None|RelationSpec=None) -> bool:
        """ Test this spec to see if it matches a spec,
          when using a given relation and a given controlling spec to source values from

          if not given a relation, acts as a coherence check between
          self(a concrete spec) and control(the abstract source spec)
          """
        match relation:
            case None:
                assert(control.name <= self.name)
                constraints = control.extra.keys()
            case RelationSpec(constraints=None):
                return True
            case RelationSpec(constraints=constraints):
                assert(relation.target <= self.name)

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

    def transformer_of(self) -> None|tuple[RelationSpec, RelationSpec]:
        """ If this spec can transform an artifact,
          return those relations.

          Transformers have file relations of a single solo abstract artifact
          so: 'file:>a/path/?.txt' -> 'file:>b/path/?.bib'
          (other relations can exist as well, but to be a transformer there needs to
          be only 1 in, 1 out solo file relation

          """
        match self._transform:
            case False:
                return None
            case (x,y):
                return self._transform
            case None:
                pass

        assert(TaskFlags.TRANSFORMER in self.flags)

        pre, post = None, None
        for x in self.depends_on:
            match x:
                case RelationSpec(target=TaskArtifact() as target) if LocationMeta.glob in target:
                    pass
                case RelationSpec(target=TaskArtifact() as target) if LocationMeta.abstract in target:
                    if pre is not None:
                        self._transform = False
                        return None
                    pre = x
                case _:
                    pass

        for y in self.required_for:
            match x:
                case RelationSpec(target=TaskArtifact() as target) if LocationMeta.glob in target:
                    pass
                case RelationSpec(target=TaskArtifact() as target) if LocationMeta.abstract in target:
                    if post is not None:
                        self._transform = False
                        return None
                    post = y
                case _:
                    pass

        match pre, post:
            case None, _:
                self._transform = False
                return None
            case _, None:
                self._transform = False
                return None
            case RelationSpec(), RelationSpec():
                self._transform = (pre, post)
                return self._transform

        raise ValueError("This shouldn't be possible")

class TaskSpec(_SpecUtils_m, BaseModel, arbitrary_types_allowed=True, extra="allow"):
    """ The information needed to describe a generic task.
    Optional things are shoved into 'extra', so things can use .on_fail on the tomlguard

    the cli parser can understand cli=[{}] specs
    actions                      : list[ [args] | {do='', args=[], **kwargs} ]

    Notes:
      sources = [root, ... grandparent, parent]. 'None' indicates halt on climbing source chain

    """
    name                         : str|TaskName
    doc                          : list[str]                                                               = []
    sources                      : list[TaskName|pl.Path|None]                                         = []

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
    ctor                         : CodeReference                                                       = Field(default=None, validate_default=True)
    queue_behaviour              : TaskQueueMeta                                                           = TaskQueueMeta.default
    flags                        : TaskFlags                                                               = TaskFlags.default
    _transform                   : None|Literal[False]|tuple[RelationSpec, RelationSpec]                            = None
    # task specific extras to use in state
    _default_ctor         : ClassVar[str]       = doot.constants.entrypoints.DEFAULT_TASK_CTOR_ALIAS
    _allowed_print_locs   : ClassVar[list[str]] = doot.constants.printer.PRINT_LOCATIONS
    _action_group_wipe    : ClassVar[dict]      = {"required_for": [], "setup": [], "actions": [], "depends_on": []}
    # Action Groups that are dependant on, rather than are dependencies of, this task:
    _dependant_groups    : ClassVar[list[str]]  = ["required_for", "on_fail"]

    @staticmethod
    def build(data:TomlGuard|dict|TaskName|str) -> Self:
        match data:
            case TomlGuard() | dict() if "source" in data:
                raise ValueError("source is deprecated, use 'sources'", data)
            case TomlGuard() | dict():
                return TaskSpec.model_validate(data)
            case TaskName():
                return TaskSpec(name=data)
            case str():
                return TaskSpec(name=TaskName.build(data))

    @model_validator(mode="before")
    def _convert_toml_keys(cls, data:dict) -> dict:
        """ converts a-key into a_key, and joins group+name """
        cleaned = {k.replace("-","_") : v  for k,v in data.items()}
        if "group" in cleaned and TaskName._separator not in cleaned["name"]:
            cleaned['name'] = TaskName._separator.join([cleaned['group'], cleaned['name']])
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

        if TaskFlags.TRANSFORMER not in self.flags:
            self._transform = False

        self.name.meta |= self.flags
        return self

    @field_validator("name", mode="before")
    def _validate_name(cls, val):
        match val:
            case TaskName():
                return val
            case str():
                name = TaskName.build(val)
                return name
            case _:
                raise TypeError("A TaskSpec Name should be a str or TaskName", val)

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
                default_alias = TaskSpec._default_ctor
                coderef_str   = doot.aliases.task[default_alias]
                return CodeReference.build(coderef_str)
            case EntryPoint():
                return CodeReference.build(val)
            case CodeReference():
                return val
            case type()|str():
                return CodeReference.build(val)
            case _:
                return CodeReference.build(val)

    @field_validator("queue_behaviour", mode="before")
    def _validate_queue_behaviour(cls, val):
        match val:
            case TaskQueueMeta():
                return val
            case str():
                return TaskQueueMeta.build(val)
            case _:
                raise ValueError("Queue Behaviour needs to be a str or a TaskQueueMeta enum", val)

    @field_validator("sources", mode="before")
    def _validate_sources(cls, val):
        """ builds the soures list, converting strings to task names,

          """
        match val:
            case None:
                val = []
            case list():
                pass
            case _:
                val = [val]

        result = []
        for x in val:
            match x:
                case "None" | None:
                    result.append(None)
                case TaskName() | pl.Path():
                    result.append(x)
                case str():
                    try:
                        name = TaskName.build(x)
                        result.append(name)
                    except (ValueError, ValidationError):
                        result.append(pl.Path(x))

        return result

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

    def specialize_from(self, data:dict|TaskSpec) -> TaskSpec:
        """
          apply data over the top of self.
          a *single* application, as a spec on it's own has no means to look up other specs,
          which is the tracker's responsibility.

          so source chain: [root..., self, data]
        """
        match data:
            case dict():
                specialized = dict(self)
                specialized.update(data)
                return TaskSpec.build(specialized)
            case TaskSpec() if self is data:
                # specializing on self, just instantiate a name
                specialized           = dict(self)
                specialized['name']   = self.name.instantiate()
                # Otherwise theres interference:
                specialized['sources'] = self.sources[:] + [self.name]
                return TaskSpec.build(specialized)
            case TaskSpec(sources=[*xs, TaskName() as x] ) if not x <= self.name:
                raise doot.errors.DootTaskTrackingError("Tried to specialize a task that isn't based on this task", str(data.name), str(self.name), str(data.sources))
            case TaskSpec(ctor=ctor) if self.ctor != ctor and ctor != TaskSpec._default_ctor:
                raise doot.errors.DootTaskTrackingError("Unknown ctor for spec", data.ctor)
            case TaskSpec():
                specialized = dict(self)
                specialized.update({k:v for k,v in dict(data).items() if k in data.model_fields_set})

        # Then special updates
        specialized['name']   = data.name.instantiate()
        specialized['sources'] = self.sources[:] + [self.name, data.name]

        specialized['actions']      = self.actions      + data.actions
        specialized["depends_on"]   = self.depends_on   + data.depends_on
        specialized["required_for"] = self.required_for + data.required_for
        specialized["cleanup"]      = self.cleanup      + data.cleanup
        specialized["on_fail"]      = self.on_fail      + data.on_fail
        specialized["setup"]        = self.setup        + data.setup

        specialized['flags']        = self.flags | data.flags

        logging.debug("Specialized Task: %s on top of: %s", data.name.readable, self.name)
        return TaskSpec.build(specialized)
