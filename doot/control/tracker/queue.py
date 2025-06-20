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
from doot.workflow._interface import (TaskMeta_e, TaskStatus_e, ArtifactStatus_e, QueueMeta_e)
from doot.workflow import (ActionSpec, TaskName, TaskSpec, DootTask, TaskArtifact)

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

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from doot.workflow import RelationSpec
    from .registry import TrackRegistry
    from .network import TrackNetwork

    type Abstract[T]  = T
    type Concrete[T]  = T
    type ActionElem   = ActionSpec|RelationSpec
    type ActionGroup  = list[ActionElem]
    type Status  = ArtifactStatus_e|TaskStatus_e

##--|
from doot.workflow._interface import Task_p
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

    def queue_entry(self, target:str|Concrete[TaskName|TaskSpec]|TaskArtifact, *, from_user:bool=False, status:Maybe[Status]=None) -> Maybe[Concrete[TaskName|TaskArtifact]]:
        """
          Queue a task by name|spec|Task_p.
          registers and instantiates the relevant spec, inserts it into the _network
          Does *not* rebuild the _network

          returns a task name if the _network has changed, else None.

          kwarg 'from_user' signifies the enty is a starting target, adding cli args if necessary and linking to the root.
        """
        abs_name         : Maybe[TaskName]
        inst_name        : Concrete[TaskName]
        task_name        : Concrete[TaskName]
        target_priority  : int  = self._network._declare_priority

        match target:
            case TaskArtifact() as art:
                assert(target in self._registry.artifacts)
                self._network.connect(art, None if from_user else False)
                self.active_set.add(art)
                self._queue.add(art, priority=art.priority)
                if status:
                    self._registry.set_status(art, status)

                logging.debug("[Queue] %s : %s", self._registry.get_status(art), art)
                return art
            case TaskSpec() as spec:
                self._registry.register_spec(spec)
                if TaskName.Marks.partial in spec.name:
                    abs_name = spec.name.pop(top=False)
                else:
                    abs_name = spec.name
            case TaskName() | str():
                abs_name = self._queue_prep_name(target)

        match abs_name:
            case None:
                return None
            case TaskName() | str() as x if x not in self._registry.specs:
                raise doot.errors.TrackingError("Unrecognized task name, it may not be registered", x)
            case TaskName() as x if not x.uuid():
                inst_name = self._registry._instantiate_spec(x)
            case TaskName() as x:
                inst_name = x

        if inst_name not in self._network:
            self._network.connect(inst_name, None if from_user else False)

        self.active_set.add(inst_name)
        match self._registry.tasks.get(inst_name, None):
            case None:
                self._queue.add(inst_name, API.DECLARE_PRIORITY)
            case x:
                self._queue.add(inst_name, x.priority)
        # Apply the override status if necessary:
        match status:
            case TaskStatus_e():
                self._registry.set_status(inst_name, status)
            case None:
                status = self._registry.get_status(inst_name)

        logging.debug("[Queue] %s (P:%s) : %s", status, target_priority, inst_name[:])
        return inst_name

    def deque_entry(self, *, peek:bool=False) -> Concrete[TaskName]:
        """ remove (or peek) the top task from the _queue .
          decrements the priority when popped.
        """
        if peek:
            return self._queue.peek()

        match self._queue.pop():
            case TaskName() as focus if focus not in self._registry.tasks:
                pass
            case TaskName() as focus if self._registry.get_priority(focus) < self._network._min_priority:
                logging.warning("[Deque] Halting (Min Priority) : %s", focus[:])
                self._registry.set_status(focus, TaskStatus_e.HALTED)
            case TaskName() as focus:
                task  = self._registry.tasks[focus]
                prior = task.priority
                task.priority -= 1
                logging.debug("[Deque] %s -> %s : %s", prior, task.priority, focus[:])
            case TaskArtifact() as focus:
                focus.priority -= 1

        return focus

    def clear_queue(self) -> None:
        """ Remove everything from the task queue,

        """
        # TODO _queue the task's failure/cleanup tasks
        self.active_set =  set()
        self.task_queue = boltons.queueutils.HeapPriorityQueue()

    def _queue_prep_name(self, name:str|TaskName) -> Maybe[TaskName]:
        """ Heuristics for queueing task names

        """
        match name:
            case TaskName() if name == self._network._root_node:
                return None
            case TaskName() if name in self.active_set:
                return name
            case TaskName() if name in self._registry.tasks:
                return name
            case TaskName() if name in self._network:
                return name
            case TaskName() if name in self._registry.specs:
                return name
            case TaskName():
                raise doot.errors.TrackingError("Unrecognized queue argument provided, it may not be registered", name)
            case str():
                return self._queue_prep_name(TaskName(name))
            case _:
                return name
