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
from ._interface import TaskTracker_p
# isort: on
# ##-- end types

##-- logging
logging    = logmod.getLogger(__name__)
##-- end logging

##--|

class Tracker_abs:
    """ A public base implementation of most of a tracker
    Has three components:
    _registry          : db for specs and tasks
    _network           : the links between specs in the registry
    _queue             : the logic for determining what task to run next
    """
    _factory           : TaskFactory_p
    _subfactory        : SubTaskFactory_p
    _registry          : API.Registry_p
    _network           : API.Network_p
    _queue             : API.Queue_p

    _declare_priority  : int
    _min_priority      : int
    _is_valid           : bool

    def __init__(self, **kwargs:Any) -> None:
        factory                 = kwargs.pop("factory", TaskFactory)
        subfactory              = kwargs.pop("subfactory", SubTaskFactory)
        registry                = kwargs.pop("registry", TrackRegistry)
        network                 = kwargs.pop("network", TrackNetwork)
        queue                   = kwargs.pop("queue", TrackQueue)
        self._declare_priority  = API.DECLARE_PRIORITY
        self._min_priority      = API.MIN_PRIORITY
        self._root_node         = TaskName(API.ROOT)
        self._is_valid          = False
        self._factory           = factory()
        self._subfactory        = subfactory()
        self._registry          = registry(tracker=self)
        self._network           = network(tracker=self)
        self._queue             = queue(tracker=self)

    ##--| properties

    @property
    def specs(self) -> dict[TaskName_p, TaskSpec_i]:
        return self._registry.specs # type: ignore[attr-defined]

    @property
    def artifacts(self) -> dict[Artifact_i, set[Abstract[TaskName_p]]]:
        return self._registry.artifacts # type: ignore[attr-defined]

    @property
    def tasks(self) -> dict[Concrete[TaskName_p], Task_i]:
        return self._registry.tasks # type: ignore[attr-defined]

    @property
    def concrete(self) -> Mapping:
        return self._registry.concrete # type: ignore[attr-defined]

    @property
    def artifact_builders(self) -> Mapping:
        return self._registry.artifact_builders # type: ignore[attr-defined]

    @property
    def abstract_artifacts(self) -> Mapping:
        return self._registry.abstract_artifacts # type: ignore[attr-defined]

    @property
    def concrete_artifacts(self) -> Mapping:
        return self._registry.concrete_artifacts # type: ignore[attr-defined]

    @property
    def network(self) -> Mapping:
        return self._network._graph # type: ignore[attr-defined]

    @property
    def active(self) -> set:
            return self._queue.active_set

    @property
    def is_valid(self) -> bool:
        return self._is_valid

    ##--| setters

    @is_valid.setter
    def is_valid(self, val:bool) -> None:
        self._is_valid = val

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
                case TaskSpec_i() if x.name.uuid():
                    self._registry.register_spec(x)
                    queue += self._generate_implicit_tasks(x)
                case TaskSpec_i():
                    self._registry.register_spec(x)
                case Artifact_i():
                    self._registry._register_artifact(x) # type: ignore[attr-defined]
                case x:
                    raise TypeError(type(x))

    def queue(self, name:str|TaskName_p|TaskSpec_i|Artifact_i|DelayedSpec, *, from_user:bool=False, status:Maybe[TaskStatus_e]=None, **kwargs:Any) -> Maybe[Concrete[TaskName_p|Artifact_i]]:  # noqa: ARG002
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
        queued = self._queue.queue_entry(name, from_user=from_user, status=status)
        return queued

    def build(self, *, sources:Maybe[Literal[True]|list[Concrete[TaskName_p]|Artifact_i]]=None) -> None:
        self._network.build_network(sources=sources)

    def validate(self) -> None:
        self._network.validate_network()

    def plan(self, *args:Any) -> list:
        raise NotImplementedError()

    def clear(self) -> None:
        self._queue.clear_queue()

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
        match self.specs.get(spec.base, None):
            case TaskSpec_i() as x:
                base = x
            case None:
                raise ValueError("The Base for a delayed spec was not found", spec.base)

        match spec.applied:
            case None:
                pass
            case dict() as applied:
                data |= applied

        match spec.inject:
            case None:
                pass
            case [*xs]:
                assert(all(isinstance(x, InjectSpec_i) for x in xs)), xs
                for inj in xs:
                    # apply_from_spec
                    data |= inj.apply_from_spec(base)
            case x:
                raise TypeError(type(x))

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
                base = self.specs[x]
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
