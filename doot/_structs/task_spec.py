#!/usr/bin/env python3
"""


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
from jgdv.structs.code_ref import CodeReference
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import SpecStruct_p, ProtocolModelMeta, Buildable_p
from doot._abstract.task import Task_i
from doot._structs.action_spec import ActionSpec
from doot._structs.artifact import TaskArtifact
from doot._structs.relation_spec import RelationSpec
from doot._structs.task_name import TaskName, TaskMeta_f
from doot.structs import DKey
from doot.enums import (LocationMeta_f, RelationMeta_e, QueueMeta_e)

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

def _dicts_to_specs(deps:list[dict], *, relation=RelationMeta_e.default) -> list[ActionSpec|RelationSpec]:
    """ Convert toml provided dicts of specs into ActionSpec and RelationSpec object"""
    results = []
    for x in deps:
        match x:
            case ActionSpec() | RelationSpec():
                results.append(x)
            case { "do": action  }:
                results.append(ActionSpec.build(x))
            case _:
                results.append(RelationSpec.build(x, relation=relation))

    return results


def _prepare_action_group(group:list[str], handler:ValidatorFunctionWrapHandler, info:ValidationInfo) -> list[RelationSpec|ActionSpec]:
    """
      Validates and Builds action/relation groups,
      converting toml specified strings, list, and dicts to Artifacts (ie:files), Task Names, ActionSpecs

      As a wrap handler, it has the context of what field is being processed,
      this allows it to set the correct RelationMeta_e type

      # TODO handle callables?
    """
    if group is None:
        return []

    relation_type = RelationMeta_e.needs
    if info.field_name in TaskSpec._blocking_groups:
        relation_type = RelationMeta_e.blocks

    results = _dicts_to_specs(group, relation=relation_type)
    return handler(results)

ActionGroup = Annotated[list[ActionSpec|RelationSpec], WrapValidator(_prepare_action_group)]

class _JobUtils_m:
    """Additional utilities mixin for job based task specs"""

    def get_source_names(self) -> list[TaskName]:
        """ Get from the spec's sources just its source tasks """
        return [x for x in self.sources if isinstance(x, TaskName)]

    def gen_job_head(self) -> list[TaskSpec]:
        """
          Generate a top spec for a job, taking the jobs cleanup actions
          and using them as the head's main action.
          Cleanup relations are turning into the head's dependencies
          Depends on the job, and its reactively queued.

          Equivalent to:
          await job.depends_on()
          await job.setup()
          subtasks = job.actions()
          await subtasks
          job.head()
          await job.cleanup()
        """
        if TaskMeta_f.JOB not in self.flags:
            return []
        if (TaskMeta_f.CONCRETE | TaskMeta_f.JOB_HEAD) & self.flags:
            return []
        if (job_head:=self.name.job_head()) is self.name:
            return []

        tasks             = []
        head_section      = _dicts_to_specs(self.extra.on_fail([], list).head_actions(), relation=RelationMeta_e.needs)
        head_dependencies = [x for x in head_section if isinstance(x, RelationSpec)]
        head_actions      = [x for x in head_section if not isinstance(x, RelationSpec)]


        # build $head$
        head : TaskSpec = TaskSpec.build({
            "name"            : job_head,
            "sources"         : self.sources[:] + [self.name, None],
            "extra"           : self.extra,
            "queue_behaviour" : QueueMeta_e.reactive,
            "depends_on"      : [self.name] + head_dependencies,
            "required_for"    : [job_head.cleanup_name()] + self.required_for[:],
            "cleanup"         : self.cleanup[:],
            "flags"           : (self.flags | TaskMeta_f.JOB_HEAD) & ~TaskMeta_f.JOB,
            "actions"         : head_actions,
            })
        assert(TaskMeta_f.JOB not in head.name)
        assert(TaskMeta_f.JOB not in head.flags)
        tasks.append(head)
        # tasks.append(self.gen_cleanup_task())
        return tasks

    def gen_cleanup_task(self) -> TaskSpec:
        """ Generate a cleanup task, shifting the 'cleanup' actions and dependencies
          to 'depends_on' and 'actions'
        """
        base_deps = [self.name] + [x for x in self.cleanup if isinstance(x, RelationSpec)]
        actions   = [x for x in self.cleanup if isinstance(x, ActionSpec)]

        cleanup : TaskSpec = TaskSpec.build({
            "name"            : self.name.cleanup_name(),
            "sources"         : self.sources[:] + [self.name, None],
            "actions"         : actions,
            "extra"           : self.extra,
            "queue_behaviour" : QueueMeta_e.reactive,
            "depends_on"      : base_deps,
            "flags"           : (self.flags | TaskMeta_f.TASK) & ~TaskMeta_f.JOB,
            })
        assert(not bool(cleanup.cleanup))
        return cleanup

class _TransformerUtils_m:
    """Utilities for artifact transformers"""

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

        assert(pre.is_concrete() or post.is_concrete())
        instance = self.instantiate_onto(None)
        match self.transformer_of():
            case None:
                raise doot.errors.DootTaskTrackingError("Tried to transformer instantiate a non-transformer", self.name)
            case (x, y) if pre in x.target or post in y.target:
                # exact transform
                # replace x with pre in depends_on
                instance.depends_on.remove(x)
                instance.depends_on.append(x.instantiate(target=pre))
                # replace y with post in required_for
                instance.required_for.remove(y)
                instance.required_for.append(y.instantiate(target=post))
            case _:
                return None

        return instance

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

        assert(TaskMeta_f.TRANSFORMER in self.flags)

        pre, post = None, None
        for x in self.depends_on:
            match x:
                case RelationSpec(target=TaskArtifact() as target) if LocationMeta_f.glob in target:
                    # Globs can be in a transformer, but don't make the transformer
                    pass
                case RelationSpec(target=TaskArtifact() as target) if not target.is_concrete():
                    if pre is not None:
                        # If theres more than one applicable, its not a tranformer
                        self._transform = False
                        return None
                    pre = x
                case _:
                    pass

        for y in self.required_for:
            match y:
                case RelationSpec(target=TaskArtifact() as target) if LocationMeta_f.glob in target:
                    pass
                case RelationSpec(target=TaskArtifact() as target) if not target.is_concrete():
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

class _SpecUtils_m:
    """General utilities mixin for task specs"""

    def instantiate_onto(self, data:None|TaskSpec) -> TaskSpec:
        """ apply self over the top of data """
        match data:
            case None:
                return self.specialize_from(self)
            case TaskSpec():
                return data.specialize_from(self)
            case _:
                raise TypeError("Can't instantiate onto something not a task spec", data)

    def make(self, ensure:type=Any) -> Task_i:
        """ Create actual task instance """
        task_ctor = self.ctor.try_import(ensure=ensure)
        return task_ctor(self)

    def apply_cli_args(self, *, override=None) -> TaskSpec:
        logging.debug("Applying CLI Args to: %s", self.name)
        spec_extra : dict = dict(self.extra.items() or [])
        if 'cli' in spec_extra:
            del spec_extra['cli']

        # Apply any cli defined args
        for cli in self.extra.on_fail([]).cli():
            if cli.name not in spec_extra:
                spec_extra[cli.name] = cli.default

        source = str(override or self.name.root(top=True))
        for key,val in doot.args.on_fail({}).tasks[source]().items():
            spec_extra[key] = val

        cli_spec = self.specialize_from(spec_extra)
        return cli_spec

class TaskSpec(BaseModel, _JobUtils_m, _TransformerUtils_m, _SpecUtils_m, SpecStruct_p, Buildable_p, metaclass=ProtocolModelMeta, arbitrary_types_allowed=True, extra="allow"):
    """ The information needed to describe a generic task.
    Optional things are shoved into 'extra', so things can use .on_fail on the tomlguard

    the cli parser can understand cli=[{}] specs
    actions                      : list[ [args] | {do='', args=[], **kwargs} ]

    Notes:
      sources = [root, ... grandparent, parent]. 'None' indicates halt on climbing source chain

    """
    name                              : TaskName
    doc                               : list[str]                                                                        = []
    sources                           : list[TaskName|pl.Path|None]                                                      = []

    # Action Groups:
    actions                           : ActionGroup                                                                      = []
    required_for                      : ActionGroup                                                                      = []
    depends_on                        : ActionGroup                                                                      = []
    setup                             : ActionGroup                                                                      = []
    cleanup                           : ActionGroup                                                                      = []
    on_fail                           : ActionGroup                                                                      = []

    # Any additional information:
    version                           : str                                                                              = doot.__version__ # TODO: make dict?
    priority                          : int                                                                              = 10
    ctor                              : CodeReference                                                                    = Field(default=None, validate_default=True)
    queue_behaviour                   : QueueMeta_e                                                                      = QueueMeta_e.default
    flags                             : TaskMeta_f                                                                       = TaskMeta_f.default
    _transform                        : None|Literal[False]|tuple[RelationSpec, RelationSpec]                            = None
    # task specific extras to use in state
    _default_ctor                     : ClassVar[str]                                                                    = doot.constants.entrypoints.DEFAULT_TASK_CTOR_ALIAS
    _allowed_print_locs               : ClassVar[list[str]]                                                              = doot.constants.printer.PRINT_LOCATIONS
    _action_group_wipe                : ClassVar[dict]                                                                   = {"required_for": [], "setup": [], "actions": [], "depends_on": []}
    # Action Groups that are depended on, rather than are dependencies of, this task:
    _blocking_groups                  : ClassVar[list[str]]                                                              = ["required_for", "on_fail"]

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
            self.flags |= TaskMeta_f.DISABLED
        try:
            match self.ctor.try_import():
                case x if issubclass(x, Task_i):
                    self.flags |= x._default_flags
                    self.name.meta |= x._default_flags
                case x:
                    pass
        except ImportError as err:
            logging.warning("Ctor Import Failed for: %s : %s", self.name, self.ctor)
            self.flags |= TaskMeta_f.DISABLED
            self.ctor = None

        if TaskMeta_f.TRANSFORMER not in self.flags:
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
            case TaskMeta_f():
                return val
            case str()|list():
                return TaskMeta_f.build(val)

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
            case QueueMeta_e():
                return val
            case str():
                return QueueMeta_e.build(val)
            case _:
                raise ValueError("Queue Behaviour needs to be a str or a QueueMeta_e enum", val)

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
        return [self.depends_on, self.setup, self.actions, self.cleanup, self.on_fail]

    def action_group_elements(self) -> Iterable[ActionSpec|RelationSpec]:
        """ Get the elements of: depends_on, setup, actions, and require_for.
          *never* cleanup, which generates its own task
        """
        queue = [self.depends_on, self.setup, self.actions, self.required_for]

        for group in queue:
            for elem in group:
                yield elem

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
            case TaskSpec():
                specialized = dict(self)
                specialized.update({k:v for k,v in dict(data).items() if k in data.model_fields_set})

        # Then special updates
        specialized['name']         = data.name.instantiate()
        specialized['sources']      = self.sources[:] + [self.name, data.name]

        specialized['actions']      = self.actions      + data.actions
        specialized["depends_on"]   = self.depends_on   + data.depends_on
        specialized["required_for"] = self.required_for + data.required_for
        specialized["cleanup"]      = self.cleanup      + data.cleanup
        specialized["on_fail"]      = self.on_fail      + data.on_fail
        specialized["setup"]        = self.setup        + data.setup

        # Internal is only for initial specs, to control listing
        specialized['flags']        = (self.flags | data.flags) & (~TaskMeta_f.INTERNAL)

        logging.debug("Specialized Task: %s on top of: %s", data.name.readable, self.name)
        return TaskSpec.build(specialized)
