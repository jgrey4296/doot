#!/usr/bin/env python3
"""

"""
# ruff: noqa: N812
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
import typing
import weakref
from importlib.metadata import EntryPoint
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto, Mixin
import jgdv.structs.strang.errors as StrangErrs
from jgdv.cli import ParamSpec
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.dkey import DKey
from jgdv.structs.strang import CodeReference
from jgdv.structs.locator import Location

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.control import QueueMeta_e

# ##-- end 1st party imports

from .action_spec import ActionSpec
from .artifact import TaskArtifact
from .relation_spec import RelationMeta_e, RelationSpec
from .task_name import TaskName

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Any, Annotated
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, overload
from dataclasses import _MISSING_TYPE, InitVar, dataclass, field, fields
from pydantic import (BaseModel, BeforeValidator, Field, ValidationError,
                      ValidationInfo, ValidatorFunctionWrapHandler, ConfigDict,
                      WrapValidator, field_validator, model_validator)
from jgdv import Maybe
from doot._abstract.protocols import (Buildable_p, ProtocolModelMeta, SpecStruct_p)
from doot._abstract.task import Task_p, Job_p

if TYPE_CHECKING:
    from typing import Final
    from typing import ClassVar, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

DEFAULT_JOB : Final[str] = "job"

def _dicts_to_specs(deps:list[dict], *, relation:RelationMeta_e=RelationMeta_e.default) -> list[ActionSpec|RelationSpec]:
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

def _prepare_action_group(group:Maybe[list[str]], handler:ValidatorFunctionWrapHandler, info:ValidationInfo) -> list[RelationSpec|ActionSpec]:
    """
      Validates and Builds action/relation groups,
      converting toml specified strings, list, and dicts to Artifacts (ie:files), Task Names, ActionSpecs

      As a wrap handler, it has the context of what field is being processed,
      this allows it to set the correct RelationMeta_e type

      # TODO handle callables?
    """
    match group:
        case None | []:
            return []
        case [*xs] if info.field_name in TaskSpec._blocking_groups:
            relation_type = RelationMeta_e.blocks
            results = _dicts_to_specs(group, relation=relation_type)
        case [*xs]:
            relation_type = RelationMeta_e.needs
            results = _dicts_to_specs(group, relation=relation_type)

    return handler(results)

##--|
ActionGroup = Annotated[list[ActionSpec|RelationSpec], WrapValidator(_prepare_action_group)]
##--|

class TaskMeta_e(enum.StrEnum):
    """
      Flags describing properties of a task,
      stored in the Task_p instance itself.
    """

    TASK         = enum.auto()
    JOB          = enum.auto()
    TRANSFORMER  = enum.auto()

    INTERNAL     = enum.auto()
    JOB_HEAD     = enum.auto()
    CONCRETE     = enum.auto()
    DISABLED     = enum.auto()

    EPHEMERAL    = enum.auto()
    IDEMPOTENT   = enum.auto()
    REQ_TEARDOWN = enum.auto()
    REQ_SETUP    = enum.auto()
    IS_TEARDOWN  = enum.auto()
    IS_SETUP     = enum.auto()
    THREAD_SAFE  = enum.auto()
    STATEFUL     = enum.auto()
    STATELESS    = enum.auto()
    VERSIONED    = enum.auto()

    default      = TASK

##--|

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
        if TaskMeta_e.JOB not in self.meta:
            return []
        if self.name.is_uniq() and TaskMeta_e.JOB_HEAD in self.meta:
            return []
        if self.name.is_head() or self.name.is_cleanup():
            return []

        job_head          = self.name.de_uniq().with_head()
        tasks             = []
        head_section      = _dicts_to_specs(self.extra.on_fail([], list).head_actions(), relation=RelationMeta_e.needs)
        head_dependencies = [x for x in head_section if isinstance(x, RelationSpec) and x.target != job_head]
        head_actions      = [x for x in head_section if not isinstance(x, RelationSpec)]

        # build $head$
        head : TaskSpec = TaskSpec.build({
            "name"            : job_head,
            "sources"         : self.sources[:] + [self.name, None],
            "queue_behaviour" : QueueMeta_e.reactive,
            "depends_on"      : [self.name, *head_dependencies],
            "required_for"    : self.required_for[:],
            "cleanup"         : self.cleanup[:],
            "meta"           : (self.meta | {TaskMeta_e.JOB_HEAD}) - {TaskMeta_e.JOB},
            "actions"         : head_actions,
            **self.extra,
            })
        assert(TaskMeta_e.JOB not in head.meta)
        tasks.append(head)
        return tasks

    def gen_cleanup_task(self) -> list[TaskSpec]:
        """ Generate a cleanup task, shifting the 'cleanup' actions and dependencies
          to 'depends_on' and 'actions'
        """
        if self.name.is_cleanup():
            return []

        cleanup_name       = self.name.de_uniq().with_cleanup()
        base_deps          = [self.name] + [x for x in self.cleanup if isinstance(x, RelationSpec) and x.target != cleanup_name]
        actions            = [x for x in self.cleanup if isinstance(x, ActionSpec)]

        cleanup : TaskSpec = TaskSpec.build({
            "name"            : cleanup_name,
            "sources"         : self.sources[:] + [self.name, None],
            "actions"         : actions,
            "queue_behaviour" : QueueMeta_e.reactive,
            "depends_on"      : base_deps,
            "meta"           : (self.meta | {TaskMeta_e.TASK}) - {TaskMeta_e.JOB},
            **self.extra,
            })
        assert(not bool(cleanup.cleanup))
        return [cleanup]

class _TransformerUtils_m:
    """Utilities for artifact transformers"""

    def instantiate_transformer(self, target:TaskArtifact|tuple[TaskArtifact, TaskArtifact]) -> Maybe[TaskSpec]:
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
                raise doot.errors.TrackingError("Tried to transformer to_uniq a non-transformer", self.name)
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

    def transformer_of(self) -> Maybe[tuple[RelationSpec, RelationSpec]]:
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

        assert(TaskMeta_e.TRANSFORMER in self.meta)

        pre, post = None, None
        for x in self.depends_on:
            match x:
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
                case RelationSpec(target=TaskArtifact() as target) if Location.bmark_e.glob in target:
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

    @classmethod
    def build(cls, data:ChainGuard|dict|TaskName|str) -> Self:
        match data:
            case ChainGuard() | dict() if "source" in data:
                raise ValueError("source is deprecated, use 'sources'", data)
            case ChainGuard() | dict():
                return cls(**data)
            case TaskName():
                return cls(name=data)
            case str():
                return cls(name=TaskName(data))

    def instantiate_onto(self, data:Maybe[TaskSpec]) -> TaskSpec:
        """ apply self over the top of data """
        match data:
            case None:
                return self.specialize_from(self)
            case TaskSpec():
                return data.specialize_from(self)
            case _:
                raise TypeError("Can't to_uniq onto something not a task spec", data)

    def specialize_from(self, data:dict|TaskSpec) -> TaskSpec:
        """ apply data on top of self"""
        match data:
            case {"_add_suffix": str() as suff}:
                # When an injection adds a suffix, it occurs here
                specialized = dict(self)
                specialized.update(data)
                specialized['name'] = self.name.push(suff)
                del specialized['_add_suffix']
                return TaskSpec.build(specialized)
            case dict():
                specialized = dict(self)
                specialized.update(data)
                return TaskSpec.build(specialized)
            case TaskSpec() if self is data:
                # specializing on self, just to_uniq a name
                specialized           = dict(self)
                specialized['name']   = self.name.to_uniq()
                # Otherwise theres interference:
                specialized['sources'] = self.sources[:] + [self.name]
                return TaskSpec.build(specialized)
            case TaskSpec(sources=[*xs, TaskName() as x] ) if not x <= self.name:
                raise doot.errors.TrackingError("Tried to specialize a task that isn't based on this task", str(data.name), str(self.name), str(data.sources))
            case TaskSpec():
                return self._specialize_merge(data)
            case _:
                raise TypeError("Unexpected type for specializing spec", data)

    def _specialize_merge(self, data:dict|TaskSpec) -> TaskSpec:
        """
          apply data over the top of self.
          a *single* application, as a spec on it's own has no means to look up other specs,
          which is the tracker's responsibility.

          so source chain: [root..., self, data]
        """

        specialized = dict(self)
        specialized.update({k:v for k,v in dict(data).items() if k in data.model_fields_set})

        # Then special updates
        specialized['name']         = data.name.to_uniq()
        specialized['sources']      = self.sources[:] + [self.name, data.name]

        specialized['actions']      = self.actions      + data.actions
        specialized["depends_on"]   = self.depends_on   + data.depends_on
        specialized["required_for"] = self.required_for + data.required_for
        specialized["cleanup"]      = self.cleanup      + data.cleanup
        specialized["on_fail"]      = self.on_fail      + data.on_fail
        specialized["setup"]        = self.setup        + data.setup

        # Internal is only for initial specs, to control listing
        specialized['meta']        = set()
        specialized['meta'].update(self.meta)
        specialized['meta'].update(data.meta)
        specialized['meta'].difference_update({TaskMeta_e.INTERNAL})

        logging.debug("Specialized Task: %s on top of: %s", data.name.readable, self.name)
        return TaskSpec.build(specialized)

    @property
    def param_specs(self) -> list:
        result = []
        for x in self.extra.on_fail([]).cli():
            result.append(ParamSpec.build(x))
        else:
            return result

    @property
    def params(self) -> dict:
        return self.model_extra

    def make(self, ensure:type=Any) -> Task_p:
        """ Create actual task instance """
        match self.ctor(check=ensure):
            case ImportError() as err:
                raise err
            case task_ctor:
                return task_ctor(self)

    def apply_cli_args(self, *, override:Maybe[str]=None) -> TaskSpec:
        logging.debug("Applying CLI Args to: %s", self.name)
        spec_extra : dict = dict(self.extra.items() or [])
        if 'cli' in spec_extra:
            del spec_extra['cli']

        # Apply any cli defined args
        for cli in self.extra.on_fail([]).cli():
            if cli.name not in spec_extra:
                spec_extra[cli.name] = cli.default

        source = str(override or self.name.pop(top=True))

        tasks = doot.args.on_fail({})
        for key,val in doot.args.on_fail({}).sub[source]().items():
            spec_extra[key] = val

        cli_spec = self.specialize_from(spec_extra)
        return cli_spec

##--|

@Proto(SpecStruct_p, Buildable_p, check=True)
@Mixin(_JobUtils_m, _TransformerUtils_m, _SpecUtils_m)
class _TaskSpecBase:
    pass

class TaskSpec(_TaskSpecBase, BaseModel, arbitrary_types_allowed=True, extra="allow"):
    """ The information needed to describe a generic task.
    Optional things are shoved into 'extra', so things can use .on_fail on the chainguard

    the cli parser can understand cli=[{}] specs
    actions                      : list[ [args] | {do='', args=[], **kwargs} ]

    Notes:
      sources = [root, ... grandparent, parent]. 'None' indicates halt on climbing source chain

    """

    ##--|
    name                              : TaskName
    doc                               : Maybe[list[str]]                                                                 = []
    sources                           : list[Maybe[TaskName|pl.Path]]                                                    = []

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
    meta                              : set[TaskMeta_e]                                                                  = set()
    _transform                        : Maybe[Literal[False]|tuple[RelationSpec, RelationSpec]]                          = None
    # task specific extras to use in state
    _default_ctor                     : ClassVar[str]                                                                    = doot.constants.entrypoints.DEFAULT_TASK_CTOR_ALIAS
    _allowed_print_locs               : ClassVar[tuple[str]]                                                             = tuple(doot.constants.printer.PRINT_LOCATIONS)
    _action_group_wipe                : ClassVar[dict]                                                                   = {"required_for": [], "setup": [], "actions": [], "depends_on": []}
    # Action Groups that are depended on, rather than are dependencies of, this task:
    _blocking_groups                  : ClassVar[tuple[str]]                                                              = tuple(["required_for", "on_fail"])

    mark_e                            : ClassVar[enum.Enum]                                                               = TaskMeta_e

    @model_validator(mode="before")
    def _convert_toml_keys(cls, data:dict) -> dict:
        """ converts a-key into a_key, and joins group+name """
        cleaned = {k.replace("-","_") : v  for k,v in data.items()}
        if "group" in cleaned and TaskName._separator not in cleaned["name"]:
            cleaned['name'] = TaskName._separator.join([cleaned['group'], cleaned['name']])
            del cleaned['group']
        return cleaned

    @model_validator(mode="after")
    def _validate_metadata(self) -> Self:
        if self.extra.on_fail(False).disabled(): # noqa: FBT003
            self.meta.add(TaskMeta_e.DISABLED)

        if TaskName.bmark_e.extend in self.name and TaskMeta_e.JOB_HEAD not in self.meta:
            self.meta.add(TaskMeta_e.JOB)

        match self.ctor():
            case ImportError() as err:
                logging.warning("Ctor Import Failed for: %s : %s", self.name, self.ctor)
                self.meta.add(TaskMeta_e.DISABLED)
                self.ctor = None
            case x if TaskMeta_e.JOB in self.meta and not isinstance(x, Job_p):
                self.ctor = CodeReference(doot.aliases.task[DEFAULT_JOB])
            case None:
                pass
            case x if issubclass(x, Task_p):
                self.meta.add(x._default_flags)

        if TaskMeta_e.TRANSFORMER not in self.meta:
            self._transform = False

        return self

    @field_validator("name", mode="before")
    def _validate_name(cls, val) -> TaskName:
        match val:
            case TaskName():
                return val
            case str():
                try:
                    name = TaskName(val)
                except StrangErrs.StrangError as err:
                    raise ValueError(*err.args) from err
                else:
                    return name
            case _:
                raise TypeError("A TaskSpec Name should be a str or TaskName", val)

    @field_validator("meta", mode="before")
    def _validate_meta(cls, val) -> set:
        match val:
            case TaskMeta_e():
                return {val}
            case str():
                vals = [val]
            case set() | list():
                vals = val

        return {x if isinstance(x, TaskMeta_e) else TaskMeta_e[x] for x in vals}

    @field_validator("ctor", mode="before")
    def _validate_ctor(cls, val) -> CodeReference:
        match val:
            case None:
                default_alias = TaskSpec._default_ctor
                coderef_str   = doot.aliases.task[default_alias]
                return CodeReference(coderef_str)
            case EntryPoint():
                return CodeReference(val)
            case CodeReference():
                return val
            case type()|str():
                return CodeReference(val)
            case _:
                return CodeReference(val)

    @field_validator("queue_behaviour", mode="before")
    def _validate_queue_behaviour(cls, val) -> QueueMeta_e:
        match val:
            case QueueMeta_e():
                return val
            case str():
                return QueueMeta_e.build(val)
            case _:
                raise ValueError("Queue Behaviour needs to be a str or a QueueMeta_e enum", val)

    @field_validator("sources", mode="before")
    def _validate_sources(cls, val) -> list:
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
                        name = TaskName(x)
                        result.append(name)
                    except (StrangErrs.StrangError, ValueError, ValidationError):
                        result.append(pl.Path(x))
                case x:
                    raise TypeError("Bad Typed Source", x)

        return result

    def __hash__(self):
        return hash(str(self.name))

    @property
    def extra(self) -> ChainGuard:
        return ChainGuard(self.model_extra)

    @property
    def action_groups(self) -> list[list]:
        return [self.depends_on, self.setup, self.actions, self.cleanup, self.on_fail]

    def action_group_elements(self) -> Iterable[ActionSpec|RelationSpec]:
        """ Get the elements of: depends_on, setup, actions, and require_for.
          *never* cleanup, which generates its own task
        """
        queue = [self.depends_on, self.setup, self.actions, self.required_for]

        for group in queue:
            yield from group
