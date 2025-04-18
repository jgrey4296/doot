#!/usr/bin/env python3
"""

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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import boltons.queueutils
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.enums import (QueueMeta_e, TaskMeta_e, TaskStatus_e, ArtifactStatus_e)
from doot.structs import (ActionSpec, TaskArtifact, TaskName, TaskSpec)
from doot.task.core.task import DootTask

# ##-- end 1st party imports

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
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from doot._structs.relation_spec import RelationSpec
    from .track_registry import TrackRegistry
    from .track_network import TrackNetwork

    type Abstract[T]  = T
    type Concrete[T]  = T
    type ActionElem   = ActionSpec|RelationSpec
    type ActionGroup  = list[ActionElem]
    type Status  = ArtifactStatus_e|TaskStatus_e

##--|
from doot._abstract import Task_p
# isort: on
# ##-- end types

##-- logging
logging          = logmod.getLogger(__name__)
logging.disabled = False
##-- end logging

##--|

class _Reactive_m:

    def _maybe_implicit_queue(self, task:Task_p) -> None:
        """ tasks can be activated for running by a number of different conditions.
          this handles that logic
          """
        if task.spec.name in self.active_set:
            return

        match task.spec.queue_behaviour:
            case QueueMeta_e.auto:
                self.queue_entry(task.name)
            case QueueMeta_e.reactive:
                self._network.nodes[task.name][API.REACTIVE_ADD] = True
            case QueueMeta_e.default:
                # Waits for explicit _queue
                pass
            case _:
                raise doot.errors.TrackingError("Unknown _queue behaviour specified: %s", task.spec.queue_behaviour)

    def _reactive_queue(self, focus:Concrete[TaskName]) -> None:
        """ Queue any known task in the _network that auto-reacts to a focus """
        for adj in self._network.adj[focus]:
            if self._network.nodes[adj].get(API.REACTIVE_ADD, False):
                self.queue_entry(adj, silent=True)

    def _reactive_fail_queue(self, focus:Concrete[TaskName]) -> None:
        """ TODO: make reactive failure tasks that can be triggered from
          a tasks 'on_fail' collection
          """
        raise NotImplementedError()

##--|

class TrackQueue:
    """ The queue of active tasks. """

    active_set             : list[Concrete[TaskName]|TaskArtifact]
    execution_trace        : list[Concrete[TaskName|TaskArtifact]]
    _registry              : TrackRegistry
    _network               : TrackNetwork
    _queue                 : boltons.queueutils.HeapPriorityQueue

    def __init__(self, registry:TrackRegistry, network:TrackNetwork):
        self._registry              = registry
        self._network               = network
        self.active_set             = set()
        self.execution_trace        = []
        self._queue                 = boltons.queueutils.HeapPriorityQueue()

    def __bool__(self) -> bool:
        return self._queue.peek(default=None) is not None

    def deque_entry(self, *, peek:bool=False) -> Concrete[TaskName]:
        """ remove (or peek) the top task from the _queue .
          decrements the priority when popped.
        """
        if peek:
            return self._queue.peek()

        match self._queue.pop():
            case TaskName() as focus if self._registry.tasks[focus].priority < self._network._min_priority:
                logging.user("Task halted due to reaching minimum priority while tracking: %s", focus)
                self._registry.set_status(focus, TaskStatus_e.HALTED)
            case TaskName() as focus:
                self._registry.tasks[focus].priority -= 1
                logging.detail("Task %s: Priority Decrement to: %s", focus, self._registry.tasks[focus].priority)
            case TaskArtifact() as focus:
                focus.priority -= 1

        return focus

    def queue_entry(self, name:str|Concrete[TaskName|TaskSpec]|TaskArtifact|Task_p, *, from_user:bool=False, status:Maybe[Status]=None) -> Maybe[Concrete[TaskName|TaskArtifact]]:
        """
          Queue a task by name|spec|Task_p.
          registers and instantiates the relevant spec, inserts it into the _network
          Does *not* rebuild the _network

          returns a task name if the _network has changed, else None.

          kwarg 'from_user' signifies the enty is a starting target, adding cli args if necessary and linking to the root.
        """

        prepped_name : Maybe[TaskName|TaskArtifact] = None
        # Prep the task: register and instantiate
        match name:
            case TaskSpec() as spec:
                self._registry.register_spec(spec)
                return self.queue_entry(spec.name, from_user=from_user, status=status)
            case Task_p() as task if task.name not in self._registry.tasks:
                self._registry.register_spec(task.spec)
                instance = self._registry._instantiate_spec(task.name, add_cli=from_user)
                # update the task with its concrete spec
                task.spec = self._registry.specs[instance]
                self._network.connect(instance, None if from_user else False)
                prepped_name = self._registry._make_task(instance, task_obj=task)
            case TaskArtifact() if name in self._network.nodes:
                prepped_name = name
            case TaskName() if name == self._network._root_node:
                prepped_name = None
            case TaskName() if name in self.active_set:
                prepped_name = name
            case TaskName() if name in self._registry.tasks:
                prepped_name  = self._registry.tasks[name].name
            case TaskName() if name in self._network:
                prepped_name = name
            case TaskName() if not from_user and (instance:=self._registry._maybe_reuse_instantiation(name)) is not None:
                prepped_name = instance
                self._network.connect(instance, None if from_user else False)
            case TaskName() if name in self._registry.specs:
                assert(not TaskName(name).is_uniq()), name
                instance : TaskName = self._registry._instantiate_spec(name, add_cli=from_user)
                self._network.connect(instance, None if from_user else False)
                prepped_name = instance
            case TaskName():
                raise doot.errors.TrackingError("Unrecognized queue argument provided, it may not be registered", name)
            case str():
                return self.queue_entry(TaskName(name), from_user=from_user)
            case _:
                raise doot.errors.TrackingError("Unrecognized queue argument provided, it may not be registered", name)

        ## --
        if prepped_name is None:
            return None
        assert(prepped_name in self._network)

        final_name      : Maybe[TaskName|TaskArtifact] = None
        target_priority : int                        = self._network._declare_priority
        match prepped_name:
            case TaskName() if TaskMeta_e.JOB_HEAD in prepped_name:
                assert(prepped_name.is_uniq())
                assert(prepped_name in self._registry.specs)
                final_name      = self._registry._make_task(prepped_name)
                target_priority = self._registry.tasks[final_name].priority
            case TaskName() if TaskMeta_e.JOB in prepped_name:
                assert(prepped_name.is_uniq())
                assert(prepped_name in self._registry.specs)
                final_name      = self._registry._make_task(prepped_name)
                target_priority = self._registry.tasks[final_name].priority
            case TaskName():
                assert(prepped_name.is_uniq())
                assert(prepped_name in self._registry.specs)
                final_name      = self._registry._make_task(prepped_name)
                target_priority = self._registry.tasks[final_name].priority
            case TaskArtifact():
                assert(prepped_name in self._registry.artifacts)
                final_name = prepped_name
                target_priority = prepped_name.priority

        self.active_set.add(final_name)
        self._queue.add(final_name, priority=target_priority)
        # Apply the override status if necessary:
        match status:
            case TaskStatus_e() | ArtifactStatus_e():
                self._registry.set_status(final_name, status)
            case None:
                status = self._registry.get_status(final_name)
        logging.trace("Queued Entry at priority: %s, status: %s: %s", target_priority, status, final_name)
        return final_name

    def clear_queue(self) -> None:
        """ Remove everything from the task queue,

        """
        # TODO _queue the task's failure/cleanup tasks
        self.active_set =  set()
        self.task_queue = boltons.queueutils.HeapPriorityQueue()
