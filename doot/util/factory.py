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
import jgdv.structs.strang.errors as StrangErrs
from jgdv import Mixin, Proto
from jgdv._abstract.protocols import Buildable_p, SpecStruct_p
from jgdv._abstract.pydantic_proto import ProtocolModelMeta
from jgdv.cli import ParamSpec, ParamSpecMaker_m
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.dkey import DKey
from jgdv.structs.locator import Location
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.workflow import (ActionSpec, DootJob, DootTask, InjectSpec,
                           RelationSpec, TaskArtifact, TaskName, TaskSpec)
from doot.workflow import _interface as API
from doot.workflow._interface import (ActionSpec_i, InjectSpec_i, Job_p,
                                      RelationMeta_e, RelationSpec_i, Task_i,
                                      Task_p, TaskMeta_e, TaskName_p,
                                      TaskSpec_i, Artifact_i)

# ##-- end 1st party imports

# ##-| Local
from ._interface import SubTaskFactory_p, TaskFactory_p, DelayedSpec
# # End of Imports.

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Any, Annotated, override
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, overload
from dataclasses import _MISSING_TYPE, InitVar, dataclass, field, fields
from pydantic import (BaseModel, BeforeValidator, Field, ValidationError,
                      ValidationInfo, ValidatorFunctionWrapHandler, ConfigDict,
                      WrapValidator, field_validator, model_validator)

if TYPE_CHECKING:
    from jgdv import Maybe
    import enum
    from typing import Final
    from typing import ClassVar, LiteralString
    from typing import Never, Self, Literal, _SpecialType
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    type SpecialType = _SpecialType

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

##--| Consts
DEFAULT_ALIAS     : Final[str]             = doot.constants.entrypoints.DEFAULT_TASK_CTOR_ALIAS
DEFAULT_BLOCKING  : Final[tuple[str, ...]] = ("required_for", "on_fail")
DEFAULT_RELATION   : Final[RelationMeta_e] = RelationMeta_e.default()
##--| Utils

##--|

@Proto(TaskFactory_p)
class TaskFactory:
    """
    Factory to create task specs, instantiate them, and make tasks

    build        : data          -> spec
    delay        : data          -> delayed -> spec
    instantiate  : spec          -> spec(name=name[uuid])
    reify        : spec,partial  -> spec
    over         : orig,plus     -> spec(plus<orig, name..<+>[uuid])
    under        : orig,plus     -> spec(orig<plus, name..<+>[uuid])
    make         : spec          -> task

    """
    spec_ctor : type[TaskSpec_i]
    task_ctor : type[Task_p]
    job_ctor  : type[Job_p]

    def __init__(self, *, spec_ctor:Maybe[type]=None, task_ctor:Maybe[type]=None, job_ctor:Maybe[type]=None):
        x : type[Any]
        match spec_ctor:
            case None:
                match CodeReference(doot.aliases.task.spec)():
                    case type() as ref:
                        self.spec_ctor  = ref
                    case Exception() as err:
                        raise err
            case type() as x:
                self.spec_ctor = x

        match task_ctor:
            case None:
                match CodeReference(doot.aliases.task.task)():
                    case type() as ref:
                         self.task_ctor = ref
                    case Exception() as err:
                        raise err
            case type() as x:
                self.task_ctor = x

        match job_ctor:
            case None:
                match CodeReference(doot.aliases.task.job)():
                    case type() as ref:
                        self.job_ctor = ref
                    case Exception() as err:
                        raise err
            case type() as x:
                self.job_ctor = x

    ##--| Spec manipulation

    def build(self, data:ChainGuard|dict|TaskName_p|str) -> TaskSpec_i:
        result : TaskSpec_i
        match data:
            case TaskSpec_i():
                result = data
            case ChainGuard() | dict() if "source" in data:
                raise ValueError("source is deprecated, use 'sources'", data)
            case ChainGuard() | dict():
                result = self.spec_ctor(**data)
            case TaskName():
                result = self.spec_ctor(name=data) # type: ignore[call-arg]
            case str():
                result = self.spec_ctor(name=TaskName(data)) # type: ignore[call-arg]
            case x:
                raise TypeError(type(x))

        return result

    def delay(self, *, base:TaskName_p, target:TaskName_p, inject:Maybe[InjectSpec_i]=None, applied:Maybe[dict]=None, overrides:dict) -> DelayedSpec:
        """
        Build data structure that the registry will process into a full spec
        """
        result : DelayedSpec = DelayedSpec(base=TaskName(base),
                                           target=TaskName(target),
                                           inject=inject,
                                           applied=applied,
                                           overrides=overrides,
                                           )

        return result

    def instantiate(self, obj:TaskSpec_i, *, extra:Maybe[Mapping]=None) -> TaskSpec_i:
        """
        Return this spec, copied with a uniq name
        """
        result    : TaskSpec_i
        instance  : TaskSpec_i
        # TODO use model_copy(update={...})
        instance      = obj.model_copy()
        instance.generated_names.clear()
        match extra:
            case None:
                result = instance
            case dict():
                result = self.merge(bot=instance, top=extra)
            case x:
                raise TypeError(type(x))

        result.name = self._prep_name(obj.name, suffix=False).to_uniq()
        assert(result.name.uuid())
        return result

    def merge(self, top:dict|TaskSpec_i, bot:dict|TaskSpec_i, *, suffix:Maybe[str|Literal[False]]=None, name:Maybe[TaskName_p]=None) -> TaskSpec_i:
        """ bot + top -> TaskSpec """
        result     : dict
        base_name  : TaskName_p
        top_data   : dict
        bot_data   : dict
        ##--|
        if bot is top:
            raise doot.errors.TrackingError("Tried to apply a spec over itself", top, bot)

        ##--| prepare
        match bot:
            case dict():
                bot_data = bot
            case TaskSpec_i():
                bot_data = bot.model_dump()
        match top:
            case dict():
                top_data = top
            case TaskSpec_i():
                top_data = top.model_dump()
        ##--|
        result          = self._specialize_merge(bot=bot_data, top=top_data)
        match name:
            case TaskName_p():
                result['name']  = name
            case _:
                base_name       = top_data.get('name', None) or bot_data['name']
                result['name']  = self._prep_name(base_name, suffix=suffix)
        ##--|
        return self.build(result)

    ##--| Task construction

    def make(self, obj:TaskSpec_i, ensure:Any=None) -> Task_p:
        """ Create actual task instance

        if no spec_ctor has been specified, uses the default spec_ctor for job/task
        """
        task : Task_p
        match obj.ctor: # Get the ctor
            case None if TaskMeta_e.JOB in obj.meta:
                ctor = self.job_ctor
            case None:
                ctor = self.task_ctor
            case CodeReference() as x:
                match x(check=ensure):
                    case type() as val:
                        ctor = val
                    case Exception() as err:
                        raise err
            case x:
                raise TypeError(type(x))

        assert(ctor is not None)
        task = ctor(obj)

        return task

    ##--| utils

    def get_source_names(self, obj:TaskSpec_i) -> list[TaskName_p]:
        """ Get from the spec's sources just its source tasks """
        val = [x for x in obj.sources if isinstance(x, TaskName)]
        return cast("list[TaskName_p]", val)

    def action_groups(self, obj:TaskSpec_i) -> Iterable[Iterable]:
        return [obj.depends_on, obj.setup, obj.actions, obj.cleanup, obj.on_fail]

    def action_group_elements(self, obj:TaskSpec_i) -> Iterable[ActionSpec_i|RelationSpec_i]:
        """ Get the elements of: depends_on, setup, actions, and require_for.
        """
        groups : Iterable[Iterable] = [obj.depends_on, obj.setup, obj.actions, obj.required_for]
        for group in groups:
            yield from group

    def _specialize_merge(self, *, bot:dict, top:dict) -> dict:
        """
          Apply top over the top of bot

        Combines, rather than overrides, particular values.

        """
        x            : Any
        y            : Any
        specialized  : dict
        sources      : set   = set()
        merge_keys   : list  = ["actions", "depends_on", "required_for", "cleanup", "on_fail", "setup"]

        specialized          = dict(bot)
        specialized |= dict(top)
        if 'name' in specialized:
            del specialized['name']

        # Extend sources
        match bot.get('sources', []), top.get('sources', []):
            case x, y if len(x) < len(y):
                sources.update(y)
            case x, _:
                sources.update(x)

        if 'name' in bot:
            sources.add(bot['name'])
        if 'name' in top:
            sources.add(top['name'])
        specialized['sources'] = list(sources)
        # Merge action groups
        for x in merge_keys:
            specialized[x] = [*bot.get(x, []), *top.get(x, [])]

        # Internal is only for initial specs, to control listing
        specialized[API.META_K] = set()
        specialized[API.META_K].update(bot.get('meta', set()))
        specialized[API.META_K].update(top.get('meta', set()))
        specialized[API.META_K].difference_update({TaskMeta_e.INTERNAL})

        return specialized

    def _prep_name(self, base:TaskName_p, *, suffix:Maybe[str|Literal[False]]=None) -> TaskName_p:
        result : TaskName_p
        match suffix:
            case None:
                result = base.push(TaskName.Marks.customised)  # type: ignore[assignment]
            case False:
                result = cast("TaskName_p", base)
            case str():
                result = base.push(suffix)  # type: ignore[assignment]
            case x:
                raise TypeError(type(x))
        ##--|
        return result.de_uniq()

@Proto(SubTaskFactory_p)
class SubTaskFactory:
    """Additional utilities mixin for job based task specs"""

    def generate_names(self, obj:TaskSpec_i) -> list[TaskName]:
        return list(obj.generated_names)

    def generate_specs(self, obj:TaskSpec_i|Artifact_i|DelayedSpec) -> list[dict]:
        result : list[dict] = []
        if not isinstance(obj, TaskSpec_i):
            return result
        if not obj.name.uuid():
            # Non-instanced specs don't generate subspecs
            return result

        logging.debug("[Generate] : %s (%s)", obj.name, len(obj.generated_names))
        needs_job_head = TaskMeta_e.JOB in obj.meta and not obj.name.is_head()
        if needs_job_head:
            # Jobs generate their head
            result += self._gen_job_head(obj)

        if not (needs_job_head or obj.name.is_cleanup()):
            # Normal tasks generate their cleanup
            # TODO shift to just executing the cleanup?
            result += self._gen_cleanup_task(obj)

        obj.generated_names.update([x['name']  for x in result])
        return result

    def _gen_job_head(self,  obj:TaskSpec_i) -> list[dict]:
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
        job_head           = obj.name.de_uniq().with_head().to_uniq()
        tasks              = []
        head_section       = self._raw_data_to_specs(obj.extra.on_fail([], list).head_actions(), relation=RelationMeta_e.needs)
        head_dependencies  = [x for x in head_section if isinstance(x, RelationSpec) and x.target != job_head]
        head_actions       = [x for x in head_section if not isinstance(x, RelationSpec)]
        ctor               = obj.extra.on_fail(None).sub_ctor()

        # build $head$
        head : dict        = {
            "name"             : job_head,
            "ctor"             : ctor,
            "sources"          : obj.sources[:] + [obj.name, None],
            "queue_behaviour"  : API.QueueMeta_e.reactive,
            "depends_on"       : [obj.name, *head_dependencies],
            "required_for"     : obj.required_for[:],
            "cleanup"          : obj.cleanup[:],
            "meta"             : (obj.meta | {TaskMeta_e.JOB_HEAD}) - {TaskMeta_e.JOB},
            "actions"          : head_actions,
            **obj.extra,
            }
        assert(TaskMeta_e.JOB not in head['meta'])
        tasks.append(head)
        return tasks

    def _gen_cleanup_task(self, obj:TaskSpec_i) -> list[dict]:
        """ Generate a cleanup task, shifting the 'cleanup' actions and dependencies
          to 'depends_on' and 'actions'
        """
        cleanup_name       = obj.name.de_uniq().with_cleanup().to_uniq()
        base_deps          = [obj.name] + [x for x in obj.cleanup if isinstance(x, RelationSpec) and x.target != cleanup_name]
        actions            = [x for x in obj.cleanup if isinstance(x, ActionSpec)]
        sources            = [obj.name]

        cleanup : dict = {
            "name"             : cleanup_name,
            "ctor"             : obj.ctor,
            "sources"          : sources,
            "queue_behaviour"  : API.QueueMeta_e.reactive,
            "depends_on"       : base_deps,
            "actions"          : actions,
            "cleanup"          : [],
            "meta"             : (obj.meta | {TaskMeta_e.TASK}) - {TaskMeta_e.JOB},
            }
        assert(not bool(cleanup['cleanup']))
        return [cleanup]

    def _raw_data_to_specs(self, deps:list[str|dict], *, relation:RelationMeta_e=DEFAULT_RELATION) -> list[ActionSpec|RelationSpec]:
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
