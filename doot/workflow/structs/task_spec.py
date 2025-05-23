#!/usr/bin/env python3
"""

"""
# mypy: disable-error-code="attr-defined"
# ruff: noqa: N812
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
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
from jgdv._abstract.protocols import (Buildable_p, SpecStruct_p)
from jgdv._abstract.pydantic_proto import ProtocolModelMeta
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors

# ##-- end 1st party imports

from .. import _interface as API
from .._interface import TaskMeta_e
from .action_spec import ActionSpec
from .inject_spec import InjectSpec
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
from .._interface import TaskSpec_i, Task_p, Job_p

if TYPE_CHECKING:
    import enum
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

##--| Consts
DEFAULT_ALIAS     : Final[str]             = doot.constants.entrypoints.DEFAULT_TASK_CTOR_ALIAS # type: ignore
DEFAULT_BLOCKING  : Final[tuple[str, ...]] = tuple(["required_for", "on_fail"])
##--| Utils

def _action_group_sort_key(val:ActionSpec|RelationSpec) -> Any:
    match val:
        case ActionSpec(): # Don't change ActionSpec ordering
            return (1,)
        case RelationSpec(target=TaskArtifact() as target):
            return (-1,)
        case RelationSpec(target=TaskName() as target):
            return (0, target)
        case x:
            raise TypeError(type(x))

def _raw_data_to_specs(deps:list[str|dict], *, relation:RelationMeta_e=RelationMeta_e.default) -> list[ActionSpec|RelationSpec]:
    """ Convert toml provided raw data (str's, dicts) of specs into ActionSpec and RelationSpec object"""
    results = []
    for x in deps:
        match x:
            case ActionSpec() | RelationSpec():
                results.append(x)
            case { "do": action  } as d:
                assert(isinstance(d, dict))
                results.append(ActionSpec.build(d))
            case _:
                results.append(RelationSpec.build(x, relation=relation))

    return results

def _prepare_action_group(group:Maybe[list[str]], handler:ValidatorFunctionWrapHandler, info:ValidationInfo) -> list[RelationSpec|ActionSpec]:
    """
      Builds, Expands, Sorts, and Validates action/relation groups,
      converting toml specified strings, list, and dicts to Artifacts (ie:files), Task Names, ActionSpecs

      As a wrap handler, it has the context of what field is being processed,
      this allows it to set the correct RelationMeta_e type

      # TODO handle callables?
    """
    match group: # Build initial Relation/Action Specs
        case None | []:
            return []
        case [*xs] if info.field_name in TaskSpec._blocking_groups:
            relation_type = RelationMeta_e.blocks
            results = _raw_data_to_specs(cast("list[str|dict]", group), relation=relation_type)
        case [*xs]:
            relation_type = RelationMeta_e.needs
            results = _raw_data_to_specs(cast("list[str|dict]", group), relation=relation_type)

    for x in results[:]: # Build Implicit Relations.
        match x:
            case RelationSpec(target=TaskName() as target, relation=rel) if target.is_cleanup(): # type: ignore[misc]
                results.append(RelationSpec.build(target.root(), relation=rel))
            case RelationSpec(target=TaskName() as target, relation=rel) if target.is_head():
                results.append(RelationSpec.build(target.root(), relation=rel))
            case _:
                pass

    action_order        = [x for x in results if isinstance(x, ActionSpec)]
    res                 = sorted(results, key=_action_group_sort_key)
    sorted_action_order = [x for x in res if isinstance(x, ActionSpec)]
    assert(x is y for x,y in zip(action_order, sorted_action_order, strict=True)), "Sorting Action Specs modifed the order"
    return handler(res)

##--|
ActionGroup = Annotated[list[ActionSpec|RelationSpec], WrapValidator(_prepare_action_group)]
##--|

class _GenerateUtils_m:
    """Additional utilities mixin for job based task specs"""

    def generate_names(self:TaskSpec_i) -> list[TaskName]:
        return list(self.generated_names)

    def generate_specs(self:TaskSpec_i) -> list[TaskSpec]:
        logging.debug("[Generate] : %s (%s)", self.name, len(self.generated_names))
        result : list[TaskSpec] = []
        if not self.name.is_uniq():
            return result

        needs_job_head = TaskMeta_e.JOB in self.meta and not self.name.is_head()
        if needs_job_head:
            result += self._gen_job_head()

        if not (needs_job_head or self.name.is_cleanup()):
            result += self._gen_cleanup_task()

        self.generated_names.update([x.name  for x in result])
        return result

    def _gen_job_head(self:TaskSpec_i) -> list[TaskSpec]:
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
        job_head          = self.name.de_uniq().with_head().to_uniq()
        tasks             = []
        head_section      = _raw_data_to_specs(self.extra.on_fail([], list).head_actions(), relation=RelationMeta_e.needs)
        head_dependencies = [x for x in head_section if isinstance(x, RelationSpec) and x.target != job_head]
        head_actions      = [x for x in head_section if not isinstance(x, RelationSpec)]

        # build $head$
        head : TaskSpec = TaskSpec.build({
            "name"            : job_head,
            "sources"         : self.sources[:] + [self.name, None],
            "queue_behaviour" : API.QueueMeta_e.reactive,
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

    def _gen_cleanup_task(self:TaskSpec_i) -> list[TaskSpec]:
        """ Generate a cleanup task, shifting the 'cleanup' actions and dependencies
          to 'depends_on' and 'actions'
        """
        cleanup_name       = self.name.de_uniq().with_cleanup().to_uniq()
        base_deps          = [self.name] + [x for x in self.cleanup if isinstance(x, RelationSpec) and x.target != cleanup_name]
        actions            = [x for x in self.cleanup if isinstance(x, ActionSpec)]
        sources            = [self.name]

        cleanup = TaskSpec.build({
            "name"            : cleanup_name,
            "sources"         : sources,
            "queue_behaviour" : API.QueueMeta_e.reactive,
            "depends_on"      : base_deps,
            "actions"         : actions,
            "cleanup"         : [],
            "meta"            : (self.meta | {TaskMeta_e.TASK}) - {TaskMeta_e.JOB},
            })
        assert(not bool(cleanup.cleanup))
        return [cleanup]

class _TransformerUtils_m:
    """Utilities for artifact transformers"""

    def instantiate_transformer(self:TaskSpec_i, target:TaskArtifact|tuple[TaskArtifact, TaskArtifact]) -> Maybe[TaskSpec]:
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
        instance = self.instantiate()
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

    def transformer_of(self:TaskSpec_i) -> Maybe[tuple[RelationSpec, RelationSpec]]:  # noqa: PLR0911, PLR0912
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
                return cast("tuple[RelationSpec, RelationSpec]", self._transform)
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
    def build(cls:type[TaskSpec_i], data:ChainGuard|dict|TaskName|str) -> TaskSpec_i:
        match data:
            case ChainGuard() | dict() if "source" in data:
                raise ValueError("source is deprecated, use 'sources'", data)
            case ChainGuard() | dict():
                return cls(**data)
            case TaskName():
                return cls(name=data)
            case str():
                return cls(name=TaskName(data))

    def instantiate(self:TaskSpec_i) -> TaskSpec:
        """
        Return this spec, copied with a uniq name
        """
        instance      = self.model_copy()
        instance.generated_names.clear()
        instance.name = self.name.to_uniq()
        return instance

    def reify_partial(self:TaskSpec_i, actual:TaskSpec) -> TaskSpec:
        if self.name[-1] != API.PARTIAL:
            raise ValueError("Tried to reify a non-partial spec", self.name)

        last_source = self.sources[-1]
        if last_source != actual.name:
            raise ValueError("Incorrect base spec for partial", self.name, last_source, actual.name)

        adjusted = dict(self) # type: ignore
        adjusted['name'] = self.name.pop()
        return actual.under(adjusted, suffix=False)

    def over(self:TaskSpec_i, data:TaskSpec, suffix:Maybe[str|Literal[False]]=None) -> TaskSpec:
        """ data + self -> TaskSpec """
        if data is self:
            raise doot.errors.TrackingError("Tried to apply a spec over itself ", self.name, data.name)
        if not data.name < self.name:
            raise doot.errors.TrackingError("Tried to apply an unrelated spec over another", self.name, data.name)
        result = data._specialize_merge(self)
        match suffix:
            case None:
                result.name = self.name.push(API.EXTENDED)
            case False:
                pass
            case str():
                result.name = self.name.push(suffix)
        return result

    def under(self:TaskSpec_i, data:dict|TaskSpec, suffix:Maybe[str|Literal[False]]=None) -> TaskSpec:
        """ self + data -> TaskSpec """
        result : TaskSpec
        match data:
            case TaskSpec() if data is self:
                raise doot.errors.TrackingError("Tried to apply a spec under itself ", self.name, data.name)
            case TaskSpec() if not self.name < data.name:
                raise doot.errors.TrackingError("Tried to apply an unrelated spec under another", self.name, data.name)
            case TaskSpec():
                result = self._specialize_merge(data)
            case dict():
                data.setdefault('name', self.name.push("<data>"))
                basic = TaskSpec.build(data)
                result = self._specialize_merge(basic)

        match suffix:
            case None:
                result.name = result.name.push(API.EXTENDED)
            case False:
                pass
            case str():
                result.name = result.name.push(suffix)

        return result

    def make(self:TaskSpec_i, *, ensure:type=Any, inject:Maybe[tuple[InjectSpec, Task_p]]=None, parent:Maybe[Task_p]=None) -> Task_p:
        """ Create actual task instance

        """
        if self.name.is_cleanup() and parent is None:
            raise ValueError("Parent was missing for cleanup task", self.name)

        # doot.report.line(f"Making: {self.name}")
        match self.ctor(check=ensure): # Make the task object
            case ImportError() as err:
                raise err
            case task_ctor:
                task = task_ctor(self)

        match parent: # Apply parent state (eg: for cleanup tasks)
            case None:
                pass
            case Task_p():
                task.state.update(parent.state)

        match inject: # Apply state injections
            case None:
                pass
            case InjectSpec() as inj, Task_p() as control:
                task.state |= inj.apply_from_state(control)
                if not inj.validate(control, task):
                    raise doot.errors.TrackingError("Late Injection Failed")

        match self.param_specs(): # Apply CLI params
            case []:
                pass
            case [*xs]:
                source    = str(self.name.root())
                task_args = doot.args.on_fail({}).sub[source]()
                for cli in xs:
                    task.state.setdefault(cli.name, task_args.get(cli.name, cli.default))

                if API.CLI_K in task.state:
                    del task.state[API.CLI_K]

        match self.extra.on_fail([])[API.MUST_INJECT_K](): # Verify all required keys have values
            case []:
                pass
            case [*xs] if bool(missing:=[x for x in xs if x not in task.state]):
                raise doot.errors.TrackingError("Task did not receive required injections", self.name, xs, task.state.keys())

        return task

    def get_source_names(self:TaskSpec_i) -> list[TaskName]:
        """ Get from the spec's sources just its source tasks """
        val = [x for x in self.sources if isinstance(x, TaskName)]
        return cast("list[TaskName]", val)

    def _specialize_merge(self:TaskSpec_i, data:TaskSpec) -> TaskSpec:
        """
          Apply data over the top of self

        Combines, rather than overrides, particular values.

        """
        specialized = dict(self)
        specialized |= dict(data)

        # Then special updates
        specialized['name']         = data.name
        specialized['sources']      = self.sources[:] + [self.name, data.name]
        specialized['actions']      = self.actions      + data.actions
        specialized["depends_on"]   = self.depends_on   + data.depends_on
        specialized["required_for"] = self.required_for + data.required_for
        specialized["cleanup"]      = self.cleanup      + data.cleanup
        specialized["on_fail"]      = self.on_fail      + data.on_fail
        specialized["setup"]        = self.setup        + data.setup

        # Internal is only for initial specs, to control listing
        specialized[API.META_K]        = set()
        specialized[API.META_K].update(self.meta)
        specialized[API.META_K].update(data.meta)
        specialized[API.META_K].difference_update({TaskMeta_e.INTERNAL})

        logging.debug("Specialized Task: %s on top of: %s", data.name.readable, self.name)
        result = TaskSpec.build(specialized)
        assert(not bool(result.generated_names))
        return result

##--|

@Proto(API.TaskSpec_i, check=True)
@Mixin(_GenerateUtils_m, _TransformerUtils_m, _SpecUtils_m)
class _TaskSpecBase:

    def param_specs(self) -> list:
        result = []
        for x in self.extra.on_fail([]).cli():
            result.append(ParamSpec.build(x))
        else:
            return result

    @property
    def params(self) -> dict:
        return self.model_extra

class TaskSpec(_TaskSpecBase, BaseModel, arbitrary_types_allowed=True, extra="allow"):
    """ The information needed to describe a generic task.
    Optional things are shoved into 'extra', so things can use .on_fail on the chainguard

    the cli parser can understand cli=[{}] specs
    actions                      : list[ [args] | {do='', args=[], **kwargs} ]

    Notes:
      sources = [root, ... grandparent, parent]. 'None' indicates halt on climbing source chain

    """

    ##--|
    name                              : TaskName                                                = Field()
    doc                               : Maybe[list[str]]                                        = Field(default_factory=list)
    sources                           : list[Maybe[TaskName|pl.Path]]                           = Field(default_factory=list)

    # Action Groups:
    actions                           : ActionGroup                                             = Field(default_factory=list)
    required_for                      : ActionGroup                                             = Field(default_factory=list)
    depends_on                        : ActionGroup                                             = Field(default_factory=list)
    setup                             : ActionGroup                                             = Field(default_factory=list)
    cleanup                           : ActionGroup                                             = Field(default_factory=list)
    on_fail                           : ActionGroup                                             = Field(default_factory=list)

    # Any additional information:
    version                           : str                                                     = Field(default=doot.__version__) # TODO: make dict?
    priority                          : int                                                     = Field(default=10)
    ctor                              : CodeReference                                           = Field(default=None, validate_default=True)
    queue_behaviour                   : API.QueueMeta_e                                         = Field(default=API.QueueMeta_e.default)
    meta                              : set[TaskMeta_e]                                         = Field(default_factory=set)
    _transform                        : Maybe[Literal[False]|tuple[RelationSpec, RelationSpec]] = None
    generated_names                   : set[TaskName]                                           = Field(init=False, default_factory=set)

    # task specific extras to use in state
    _default_ctor                     : ClassVar[str]                                           = DEFAULT_ALIAS
    # Action Groups that are depended on, rather than are dependencies of, this task:
    _blocking_groups                  : ClassVar[tuple[str]]                                    = DEFAULT_BLOCKING

    mark_e                            : ClassVar[enum.Enum]                                     = TaskMeta_e

    @model_validator(mode="before")
    def _convert_toml_keys(cls, data:dict) -> dict:
        """ converts a-key into a_key, and joins group+name """
        cleaned = {k.replace(API.DASH_S, API.USCORE_S) : v  for k,v in data.items()}
        if API.GROUP_K in cleaned and TaskName._separator not in cleaned[API.GROUP_K]:
            cleaned[API.NAME_K] = TaskName._separator.join([cleaned[API.GROUP_K], cleaned[API.NAME_K]])
            del cleaned[API.GROUP_K]
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
                self.ctor = CodeReference(doot.aliases.task[API.DEFAULT_JOB])
            case None:
                pass
            case x if isinstance(x, Task_p):
                self.meta.add(x._default_flags)

        if TaskMeta_e.TRANSFORMER not in self.meta:
            self._transform = False

        if self.name[-1] == API.PARTIAL and not bool(self.sources):
            raise ValueError("Tried to create a partial spec with no base source", self.name)

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
    def _validate_queue_behaviour(cls, val) -> API.QueueMeta_e:
        match val:
            case API.QueueMeta_e():
                return val
            case str():
                return API.QueueMeta_e.build(val)
            case _:
                raise ValueError("Queue Behaviour needs to be a str or a QueueMeta_e enum", val)

    @field_validator("sources", mode="before")
    def _validate_sources(cls, val) -> list:
        """ builds the soures list, converting strings to task names,

          """
        result = []
        for x in val:
            match x:
                case API.NONE_S | None:
                    result.append(None)
                case TaskName() if x[-1] == API.PARTIAL:
                    raise ValueError("A TaskSpec can not rely on a partial spec", x)
                case TaskName() | pl.Path():
                    result.append(x)
                case str():
                    try:
                        name = TaskName(x)
                        if name[-1] == API.PARTIAL:
                            raise ValueError("A TaskSpec can not rely on a partial spec", x)
                        result.append(name)
                    except (StrangErrs.StrangError, ValidationError):
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
