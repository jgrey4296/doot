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
from jgdv._abstract.protocols import (Buildable_p, SpecStruct_p)
from jgdv._abstract.pydantic_proto import ProtocolModelMeta
from jgdv.cli import ParamSpec, ParamSpecMaker_m
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.dkey import DKey
from jgdv.structs.locator import Location
from jgdv.structs.strang import CodeReference
import jgdv.structs.strang.errors as StrangErrs
import doot
import doot.errors
# ##-- end 3rd party imports

# ##-- 1st party imports

# ##-- end 1st party imports

from ._interface import TaskFactory_p, SubTaskFactory_p
from doot.workflow import _interface as API
from doot.workflow._interface import TaskSpec_i, Task_p, Job_p, Task_i, TaskMeta_e, RelationMeta_e, TaskName_p
from doot.workflow import ActionSpec, InjectSpec, TaskArtifact, RelationSpec, TaskName, TaskSpec, DootTask, DootJob

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

    def build(self, data:ChainGuard|dict|TaskName|str) -> TaskSpec_i:
        result : TaskSpec_i
        match data:
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

    def instantiate(self, obj:TaskSpec_i, *, extra:Maybe[Mapping|bool]=None) -> TaskSpec_i:
        """
        Return this spec, copied with a uniq name
        """
        instance : TaskSpec_i
        # TODO use model_copy(update={...})
        instance      = obj.model_copy()
        instance.generated_names.clear()
        instance.name = obj.name.to_uniq()
        match extra:
            case None | True:
                return instance
            case dict():
                extended = self.under(instance, extra)
                return extended
            case x:
                raise TypeError(type(x))


    def reify_partial(self, obj:TaskSpec_i, actual:TaskSpec_i) -> TaskSpec_i:
        """ Turn a partial spec into a full spec by applying it over an actual spec """
        adjusted : dict
        if TaskName.Marks.partial not in obj.name:
            raise ValueError("Tried to reify a non-partial spec", obj.name)

        last_source = obj.sources[-1]
        if last_source != actual.name:
            raise ValueError("Incorrect base spec for partial", obj.name, last_source, actual.name)

        adjusted          = obj.model_dump()
        adjusted['name']  = obj.name.pop(top=False)
        return self.under(actual, adjusted, suffix=False)

    def over(self, obj:TaskSpec_i, data:TaskSpec, suffix:Maybe[str|Literal[False]]=None) -> TaskSpec_i:
        """ data + obj -> TaskSpec """
        result : TaskSpec_i
        if data is obj:
            raise doot.errors.TrackingError("Tried to apply a spec over itobj ", obj.name, data.name)
        if not data.name < obj.name:
            raise doot.errors.TrackingError("Tried to apply an unrelated spec over another", obj.name, data.name)
        result = self._specialize_merge(data, obj) # type: ignore[arg-type]
        match suffix:
            case None:
                result.name = cast("TaskName_p", obj.name.push(TaskName.Marks.customised))
            case False:
                pass
            case str():
                result.name = cast("TaskName_p", obj.name.push(suffix))

        if not obj.name.uuid():
            return result
        if not result.name.uuid():
            return result.instantiate()

        return result

    def under(self, obj:TaskSpec_i, data:dict|TaskSpec, suffix:Maybe[str|Literal[False]]=None) -> TaskSpec_i:
        """ obj + data -> TaskSpec """
        result : TaskSpec_i
        match data:
            case TaskSpec() if data is obj:
                raise doot.errors.TrackingError("Tried to apply a spec under itobj ", obj.name, data.name)
            case TaskSpec() if not obj.name < data.name:
                raise doot.errors.TrackingError("Tried to apply an unrelated spec under another", obj.name, data.name)
            case TaskSpec():
                result = self._specialize_merge(obj, data)
            case dict():
                data.setdefault('name', obj.name.push(TaskName.Marks.data))
                basic = self.build(data)
                result = self._specialize_merge(obj, basic) # type: ignore[arg-type]

        match suffix:
            case None:
                result.name = cast("TaskName_p", result.name.push(TaskName.Marks.customised))
            case False:
                pass
            case str():
                result.name = cast("TaskName_p", result.name.push(suffix))

        assert(isinstance(result, TaskSpec_i)), type(result)
        if not obj.name.uuid():
            return result

        if not result.name.uuid():
            return self.instantiate(result)

        return result

    ##--| Task construction

    def make(self, obj:TaskSpec_i, **kwargs:Any) -> Task_p:  # noqa: PLR0912
        """ Create actual task instance

        if no spec_ctor has been specified, uses the default spec_ctor for job/task
        """
        ensure = kwargs.pop("ensure", None)
        inject = kwargs.pop("inject", None)
        parent = kwargs.pop("parent", None)
        # Late bind the spec_ctor if it is not explicit
        match obj.ctor:
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
                if not inj.validate(cast("Task_i", control), task):
                    raise doot.errors.TrackingError("Late Injection Failed")

        match obj.param_specs(): # Apply CLI params
            case []:
                pass
            case [*xs]:
                # Apply CLI passed params, but only as the default
                # So if override values have been injected, they are preferred
                target     = obj.name.pop(top=True)[:,:]
                task_args : dict = doot.args.on_fail({}).sub[target]()
                for cli in xs:
                    task.state.setdefault(cli.name, task_args.get(cli.name, cli.default))

                if API.CLI_K in task.state:
                    del task.state[API.CLI_K]

        match obj.extra.on_fail([])[API.MUST_INJECT_K](): # Verify all required keys have values
            case []:
                pass
            case [*xs] if bool(missing:=[x for x in xs if x not in task.state]):
                raise doot.errors.TrackingError("Task did not receive required injections", obj.name, xs, task.state.keys())

        return task

    ##--| utils

    def get_source_names(self, obj:TaskSpec_i) -> list[TaskName]:
        """ Get from the spec's sources just its source tasks """
        val = [x for x in obj.sources if isinstance(x, TaskName)]
        return cast("list[TaskName]", val)

    def _specialize_merge(self, obj:TaskSpec_i, data:TaskSpec) -> TaskSpec_i:
        """
          Apply data over the top of obj

        Combines, rather than overrides, particular values.

        """
        result : TaskSpec_i
        specialized = dict(obj) # type: ignore[call-overload]
        specialized |= dict(data)

        # Then special updates
        specialized['name']         = data.name
        specialized['sources']      = obj.sources[:] + [obj.name, data.name]
        specialized['actions']      = obj.actions      + data.actions
        specialized["depends_on"]   = obj.depends_on   + data.depends_on
        specialized["required_for"] = obj.required_for + data.required_for
        specialized["cleanup"]      = obj.cleanup      + data.cleanup
        specialized["on_fail"]      = obj.on_fail      + data.on_fail
        specialized["setup"]        = obj.setup        + data.setup

        # Internal is only for initial specs, to control listing
        specialized[API.META_K]        = set()
        specialized[API.META_K].update(obj.meta)
        specialized[API.META_K].update(data.meta)
        specialized[API.META_K].difference_update({TaskMeta_e.INTERNAL})

        logging.debug("Specialized Task: %s on top of: %s", data.name[:], obj.name)
        result = self.build(specialized)
        assert(not bool(result.generated_names))
        return result

    def action_groups(self, obj:TaskSpec_i) -> list[list]:
        return [obj.depends_on, obj.setup, obj.actions, obj.cleanup, obj.on_fail]

    def action_group_elements(self, obj:TaskSpec_i) -> Iterable[ActionSpec|RelationSpec]:
        """ Get the elements of: depends_on, setup, actions, and require_for.
        """
        groups = [obj.depends_on, obj.setup, obj.actions, obj.required_for]
        for group in groups:
            yield from group

@Proto(SubTaskFactory_p)
class SubTaskFactory:
    """Additional utilities mixin for job based task specs"""

    def generate_names(self, obj:TaskSpec_i) -> list[TaskName]:
        return list(obj.generated_names)

    def generate_specs(self, obj:TaskSpec_i) -> list[dict]:
        logging.debug("[Generate] : %s (%s)", obj.name, len(obj.generated_names))
        result : list[dict] = []
        if not obj.name.uuid():
            # Non-instanced specs don't generate subspecs
            return result

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
