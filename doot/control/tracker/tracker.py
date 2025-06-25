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
from doot.workflow._interface import ArtifactStatus_e, TaskStatus_e
from doot.workflow import ActionSpec, TaskArtifact, TaskName, TaskSpec, DootTask, RelationSpec, InjectSpec
from .network import TrackNetwork
from .queue import TrackQueue
from .registry import TrackRegistry

# ##-- end 1st party imports

from doot.util.factory import TaskFactory, SubTaskFactory
from doot.workflow._interface import RelationSpec_i, Task_i, TaskSpec_i, Artifact_i, TaskName_p, InjectSpec_i
from doot.util._interface import DelayedSpec
from . import _interface as API # noqa: N812

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
    is_valid           : bool

    def __init__(self, **kwargs:Any) -> None:
        factory                 = kwargs.pop("factory", TaskFactory)
        subfactory              = kwargs.pop("subfactory", SubTaskFactory)
        registry                = kwargs.pop("registry", TrackRegistry)
        network                 = kwargs.pop("network", TrackNetwork)
        queue                   = kwargs.pop("queue", TrackQueue)
        self._declare_priority  = API.DECLARE_PRIORITY
        self._min_priority      = API.MIN_PRIORITY
        self._root_node         = TaskName(API.ROOT)
        self.is_valid           = False
        self._factory           = factory()
        self._subfactory        = subfactory()
        self._registry          = registry(tracker=self)
        self._network           = network(tracker=self)
        self._queue             = queue(tracker=self)

    ##--| properties

    @property
    def specs(self) -> dict[TaskName, TaskSpec]:
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

    ##--| dunders

    def __bool__(self) -> bool:
        return bool(self._queue)

    ##--| public

    def register(self, *specs:TaskSpec_i|Artifact_i|DelayedSpec)-> None:
        actual : TaskSpec_i
        for x in specs:
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

    def queue(self, name:str|TaskName_p|TaskSpec_i|Artifact_i|DelayedSpec, *, from_user:bool=False, status:Maybe[TaskStatus_e]=None, **kwargs:Any) -> Maybe[Concrete[TaskName_p|Artifact_i]]:  # noqa: ARG002
        match name:
            case TaskName_p() | Artifact_i():
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
        result  : TaskSpec_i
        base    : TaskSpec_i
        data    : dict  = {}
        match self.specs.get(spec.base, None):
            case TaskSpec_i() as x:
                base = x
            case None:
                raise ValueError("The Base for a delayed spec was not found", spec.base)
        match spec.inject:
            case None:
                pass
            case InjectSpec_i() as inj:
                # apply_from_spec
                data |= inj.apply_from_spec(base)

        match spec.applied:
            case None:
                pass
            case dict() as applied:
                data |= applied

        data |= spec.overrides
        data['name'] = spec.target
        result = self._factory.merge(bot=base, top=data)
        return result

    def _reify_partial_spec(self, spec:TaskSpec_i) -> TaskSpec_i:
        assert(TaskName.Marks.partial in spec.name)
        result  : TaskSpec_i
        base    : TaskSpec_i
        target  : TaskName_p
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
        result.name = base
        return result

##--|

@Proto(API.TaskTracker_p)
class Tracker(Tracker_abs):

    def _get_priority(self, target:Concrete[TaskName|TaskArtifact]) -> int:
        return self._registry.get_priority(target) # type: ignore[attr-defined]

    def get_status(self, task:Concrete[TaskName]|TaskArtifact) -> TaskStatus_e:
        return self._registry.get_status(task) # type: ignore[attr-defined]

    def set_status(self, task:Concrete[TaskName]|TaskArtifact|Task_p, state:TaskStatus_e) -> bool:
        return self._registry.set_status(task, state) # type: ignore[attr-defined]

    def next_for(self, target:Maybe[str|TaskName]=None) -> Maybe[Task_p|TaskArtifact]:  # noqa: PLR0912, PLR0915
        """ ask for the next task that can be performed

          Returns a Task or Artifact that needs to be executed or created
          Returns None if it loops too many times trying to find a target,
          or if theres nothing left in the queue

        """
        x       : Any
        focus   : str|TaskName_p|Artifact_i
        count   : int
        result  : Maybe[Task_p|TaskArtifact]
        status  : TaskStatus_e

        logging.info("[Next.For] (Active: %s)", len(self._queue.active_set))
        if not self.is_valid:
            raise doot.errors.TrackingError("Network is in an invalid state")

        if target and target not in self._queue.active_set:
            self.queue(target, silent=True)

        count  = API.MAX_LOOP
        result = None
        while (result is None) and bool(self._queue) and 0 < (count:=count-1):
            focus   = self._queue.deque_entry()
            status  = self._registry.get_status(focus) # type: ignore[attr-defined]
            if focus not in self._queue.active_set:
                continue

            logging.debug("[Next.For.Head]: %s : %s", status, focus)

            match status:
                case TaskStatus_e.DEAD:
                    # Clear state
                    del self._registry.tasks[focus]
                    self._queue.active_set.remove(focus)
                case TaskStatus_e.DISABLED:
                    self._queue.active_set.remove(focus)
                case TaskStatus_e.TEARDOWN:
                    for succ in self._network.succ[focus]:
                        match self.queue(succ):
                            case TaskName() as x if x.is_cleanup():
                                # make the cleanup task early, to apply shared state
                                assert(isinstance(focus, TaskName))
                                self._registry.make_task(x, parent=focus)
                            case _:
                                pass
                    else:
                        # TODO for cleanup succ, move focus.state -> succ.state
                        self._registry.set_status(focus, TaskStatus_e.DEAD) # type: ignore[attr-defined]
                case ArtifactStatus_e.EXISTS:
                    # TODO artifact Exists, queue its dependents and *don't* add the artifact back in
                    self._queue.execution_trace.append(focus)
                case TaskStatus_e.SUCCESS:
                    self._queue.execution_trace.append(focus) # type: ignore[attr-defined]
                    self.queue(focus, status=TaskStatus_e.TEARDOWN)
                case TaskStatus_e.FAILED:  # propagate failure
                    self.queue(focus, status=TaskStatus_e.TEARDOWN)
                case TaskStatus_e.HALTED:  # remove and propagate halted status
                    self.queue(focus, status=TaskStatus_e.TEARDOWN)
                case TaskStatus_e.SKIPPED:
                    self.queue(focus, status=TaskStatus_e.DEAD)
                case TaskStatus_e.RUNNING:
                    self.queue(focus)
                case TaskStatus_e.READY:   # return the task if its ready
                    self.queue(focus, status=TaskStatus_e.RUNNING)
                    result = self._registry.tasks[focus]
                case TaskStatus_e.WAIT: # Add dependencies of a task to the stack
                    match self._network.incomplete_dependencies(focus): # type: ignore[attr-defined]
                        case []:
                            self.queue(focus, status=TaskStatus_e.READY)
                        case [*xs]:
                            logging.debug("Task Blocked: %s on : %s", focus, xs)
                            self.queue(focus)
                            for x in xs:
                                self.queue(x)
                case TaskStatus_e.INIT:
                    task_name = self.queue(focus, status=TaskStatus_e.WAIT)
                case ArtifactStatus_e.STALE:
                    for pred in self._network.pred[focus]:
                        self.queue(pred)
                case ArtifactStatus_e.DECLARED if bool(focus):
                    self.queue(focus, status=ArtifactStatus_e.EXISTS)
                case ArtifactStatus_e.DECLARED: # Add dependencies of an artifact to the stack
                    match self._network.incomplete_dependencies(focus):
                        case [] if not focus.is_concrete():
                            self.queue(focus, status=ArtifactStatus_e.EXISTS)
                        case []:
                            assert(not bool(focus))
                            path = focus.expand()
                            self.queue(focus)
                            # Returns the artifact, the runner can try to create
                            # it, then override the halt
                            result = focus
                        case [*xs]:
                            logging.info("Artifact Blocked, queuing producer tasks, count: %s", len(xs))
                            self.queue(focus)
                            for x in xs:
                                self.queue(x)
                case TaskStatus_e.DEFINED:
                    self.queue(focus, status=TaskStatus_e.HALTED)
                case TaskStatus_e.DECLARED:
                    assert(isinstance(focus, TaskName))
                    self._registry.make_task(focus)
                    self.queue(focus)
                case TaskStatus_e.NAMED:
                    logging.warning("A Name only was queued, it has no backing in the tracker: %s", focus)
                case x: # Error otherwise
                    raise doot.errors.TrackingError("Unknown task state", x)

        else:
            logging.info("[Next.For] <- %s", result)
            return result
