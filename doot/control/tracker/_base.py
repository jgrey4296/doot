#!/usr/bin/env python3
"""
Abstract Specs: A[n]
Concrete Specs: C[n]
Task:           T[n]

  Expansion: ∀x ∈ C[n].depends_on => A[x] -> C[x]
  Head: C[1].depends_on[A[n].$head$] => A[n] -> C[n], A[n].head -> C[n].head, connect

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
from collections import defaultdict
from itertools import chain, cycle
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.util._interface import DelayedSpec
from doot.util.factory import SubTaskFactory, TaskFactory
from doot.workflow import (ActionSpec, DootTask, InjectSpec, RelationSpec,
                           TaskArtifact, TaskName, TaskSpec)
from doot.workflow._interface import (CLI_K, Artifact_i, ArtifactStatus_e,
                                      InjectSpec_i, RelationSpec_i, Task_i,
                                      TaskName_p, TaskSpec_i, TaskStatus_e,
                                      MUST_INJECT_K)

# ##-- end 1st party imports

# ##-| Local
from . import _interface as API # noqa: N812
from .network import TrackNetwork
from .queue import TrackQueue
from .registry import TrackRegistry

# # End of Imports.

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from networkx import DiGraph

    from doot.util._interface import TaskFactory_p, SubTaskFactory_p
    type Abstract[T] = T
    type Concrete[T] = T

##--|
from doot.workflow._interface import Task_p
from ._interface import WorkflowTracker_p
# isort: on
# ##-- end types

##-- logging
logging    = logmod.getLogger(__name__)
##-- end logging

##--|

class Tracker_abs:
    """ A public base implementation of most of a tracker
    Has three components:
    _registry                : db for specs and tasks
    _network                 : the links between specs in the registry
    _queue                   : the logic for determining what task to run next
    """
    _factory                 : TaskFactory_p
    _subfactory              : SubTaskFactory_p
    _registry                : API.Registry_p
    _network                 : API.Network_p
    _queue                   : API.Queue_p

    _declare_priority        : int
    _min_priority            : int

    def __init__(self, **kwargs:Any) -> None:
        factory                       = kwargs.pop("factory", TaskFactory)
        subfactory                    = kwargs.pop("subfactory", SubTaskFactory)
        registry                      = kwargs.pop("registry", TrackRegistry)
        network                       = kwargs.pop("network", TrackNetwork)
        queue                         = kwargs.pop("queue", TrackQueue)
        self._declare_priority        = API.DECLARE_PRIORITY
        self._min_priority            = API.MIN_PRIORITY
        self._root_node               = TaskName(API.ROOT)
        self._factory                 = factory()
        self._subfactory              = subfactory()
        self._registry                = registry(tracker=self)
        self._network                 = network(tracker=self)
        self._queue                   = queue(tracker=self)

    ##--| properties

    @property
    def specs(self) -> dict[TaskName_p, API.SpecMeta_d]:
        return self._registry.specs # type: ignore[attr-defined]

    @property
    def artifacts(self) -> dict[Artifact_i, API.ArtifactMeta_d]:
        return self._registry.artifacts # type: ignore[attr-defined]

    @property
    def concrete(self) -> set:
        return self._registry.concrete # type: ignore[attr-defined]

    @property
    def abstract(self) -> set:
        assert(hasattr(self._registry, "abstract"))
        return self._registry.abstract

    @property
    def network(self) -> Mapping:
        return self._network._graph # type: ignore[attr-defined]

    @property
    def active(self) -> set:
            return self._queue.active_set

    @property
    def is_valid(self) -> bool:
        return not bool(self._network.non_expanded)

    ##--| dunders

    def __bool__(self) -> bool:
        return bool(self._queue)

    ##--| public

    def register(self, *specs:TaskSpec_i|Artifact_i|DelayedSpec)-> None:
        actual  : TaskSpec_i
        queue   : list = [*specs]
        while bool(queue):
            x = queue.pop()
            match x:
                case DelayedSpec():
                    actual = self._upgrade_delayed_to_actual(x)
                    self._registry.register_spec(actual)
                case TaskSpec_i() if TaskName.Marks.partial in x.name:
                    actual = self._reify_partial_spec(x)
                    self._registry.register_spec(actual)
                case TaskSpec_i():
                    self._registry.register_spec(x)
                case Artifact_i():
                    self._registry._register_artifact(x) # type: ignore[attr-defined]
                case x:
                    raise TypeError(type(x))

    def queue(self, name:str|TaskName_p|TaskSpec_i|Artifact_i|DelayedSpec, *, from_user:int|bool=False, status:Maybe[TaskStatus_e]=None, **kwargs:Any) -> Maybe[Concrete[TaskName_p|Artifact_i]]:  # noqa: ARG002
        queued  : TaskName_p|Artifact_i
        ##--|
        match name:
            case str() | TaskName_p() | Artifact_i():
                pass
            case DelayedSpec():
                self.register(name)
                name = name.target
            case TaskSpec_i():
                self.register(name)
                name = name.name
            case x:
                raise TypeError(type(x))
        match self._queue.queue_entry(name, from_user=from_user), status:
            case None, _:
                return None
            case TaskName_p()|Artifact_i() as queued, None:
                pass
            case TaskName_p()|Artifact_i() as queued, TaskStatus_e() as _status:
                assert(hasattr(self, "set_status"))
                self.set_status(queued, _status)
        ##--|
        assert(hasattr(self, "get_status"))
        status, priority = self.get_status(target=queued)
        logging.debug("[Tracker.Queue] : %s (S:%s, P:%s)", queued[:,:], status.name, priority)
        return queued

    def build(self, *, sources:Maybe[Literal[True]|list[Concrete[TaskName_p]|Artifact_i]]=None) -> None:
        self._network.build_network(sources=sources)

    def validate(self) -> None:
        self._network.validate_network()

    def plan(self, *args:Any) -> list:
        raise NotImplementedError()

    def clear(self) -> None:
        self._queue.clear_queue()

    def report(self, target:TaskName_p) -> dict:
        result : dict
        ##--|
        result                       = {}
        abstract                     = target.de_uniq() if target.uuid() else target
        related  : list[TaskName_p]  = [abstract]
        while bool(related):
            curr = related.pop()
            related += self.specs[curr].related
            result[str(curr)]  = {str(x) for x in self.specs[curr].related}
        else:
            assert(str(target) in result)
            return result
    ##--| internal

    def _instantiate(self, target:TaskName_p|RelationSpec_i, *args:Any, task:bool=False, **kwargs:Any) -> Maybe[TaskName_p]:
        match target:
            case TaskName_p() as x if task:
                return self._registry.make_task(x, *args, **kwargs) # type: ignore[return-value]
            case TaskName_p() as x:
                return self._registry.instantiate_spec(x, *args, **kwargs)
            case RelationSpec_i() as x:
                return self._registry.instantiate_relation(target, *args, **kwargs)
            case x:
                raise TypeError(type(x))

    def _connect(self, left:Concrete[TaskName_p]|Artifact_i, right:Maybe[Literal[False]|Concrete[TaskName_p]|Artifact_i]=None, **kwargs:Any) -> None:
        self._network.connect(left, right, **kwargs)

    def _upgrade_delayed_to_actual(self, spec:DelayedSpec) -> TaskSpec_i:
        """
        can't be in taskfactory, as it requires the registered specs
        """
        x       : Any
        result  : TaskSpec_i
        base    : TaskSpec_i
        data    : dict  = {}
        match spec:
            case DelayedSpec(base=TaskName_p() as base_name,
                             applied=dict() as applied,
                             inject=list() as injections,
                             overrides=dict() as overrides,
                             ):
                pass
            case x:
                raise TypeError(type(x))

        match self.specs.get(base_name, None):
            case API.SpecMeta_d(spec=TaskSpec_i() as base):
                pass
            case _:
                raise ValueError("The Base for a delayed spec was not found", spec.base)

        data |= applied
        for inj in injections:
            assert(isinstance(inj, InjectSpec_i))
            # apply_from_spec
            data |= inj.apply_from_spec(base)
        else:
            data |= spec.overrides
            data['name'] = spec.target
            result = self._factory.merge(bot=base, top=data)
            return result

    def _reify_partial_spec(self, spec:TaskSpec_i) -> TaskSpec_i:
        """
        converts spec(name=group::task.a.b..$partial$, sources[*_, base], data)
        into spec(name=group::a.b, data)
        using base
        can't be in the taskfactory, as it requires registered specs

        """
        x       : Any
        result  : TaskSpec_i
        base    : TaskSpec_i
        target  : TaskName_p
        ##--|
        assert(TaskName.Marks.partial in spec.name)
        match spec.sources[-1]:
            case TaskName_p() as x if x not in self.specs:
                raise ValueError("Could not find a partial spec's source", x)
            case TaskName_p() as x:
                base = self.specs[x].spec
            case x:
                raise TypeError(type(x))

        match spec.name.pop(top=False):
            case TaskName_p() as adjusted if adjusted in self.specs:
                raise doot.errors.TrackingError("Tried to reify a partial spec into one that already is registered", spec.name, adjusted)
            case TaskName_p() as x:
                target = x
            case x:
                raise TypeError(type(x))

        result = self._factory.merge(bot=base, top=spec, suffix=False)
        result.name = target
        return result

    def _generate_implicit_tasks(self, spec:TaskSpec_i) -> list[TaskSpec_i]:
        """ Generate implicit subtasks for a concrete spec """
        assert(spec.name.uuid())
        return [self._factory.build(x) for x in  self._subfactory.generate_specs(spec)]
