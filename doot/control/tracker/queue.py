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
from uuid import UUID, uuid1
import weakref

# ##-- end stdlib imports

# ##-- 3rd party imports
import boltons.queueutils
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.workflow._interface import (TaskMeta_e, TaskStatus_e, ArtifactStatus_e, QueueMeta_e, TaskName_p, TaskSpec_i, ActionSpec_i, Artifact_i)
from doot.workflow import (DootTask, TaskArtifact, TaskName)

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
    type ActionElem   = ActionSpec_i|RelationSpec
    type ActionGroup  = list[ActionElem]
    type Status  = ArtifactStatus_e|TaskStatus_e

##--|
from doot.workflow._interface import Task_i
# isort: on
# ##-- end types

##-- logging
logging          = logmod.getLogger(__name__)
logging.disabled = False
##-- end logging

##--|

class TrackQueue:
    """ The queue of active tasks. """

    active_set       : set[Concrete[TaskName_p]|Artifact_i]
    execution_trace  : list[Concrete[TaskName_p|Artifact_i]]
    # TODO use this instead of _tracker._registry and _tracker._network
    _tracker         : API.TaskTracker_i
    _queue           : boltons.queueutils.HeapPriorityQueue

    def __init__(self, *, tracker:API.TaskTracker_p) -> None:
        match tracker:
            case API.TaskTracker_i():
                self._tracker = tracker
            case x:
                raise TypeError(type(x))
        self.active_set             = set()
        self.execution_trace        = []
        self._queue                 = boltons.queueutils.HeapPriorityQueue()

    ##--| dunders
    def __bool__(self) -> bool:
        return self._queue.peek(default=None) is not None

    ##--| public
    def queue_entry(self, target:str|TaskName_p|Artifact_i, *, from_user:bool=False, status:Maybe[Status]=None) -> Maybe[Concrete[TaskName_p|Artifact_i]]:  # noqa: PLR0912
        """
          Queue a task by name|spec|Task_i.
          registers and instantiates the relevant spec, inserts it into the _tracker._network
          Does *not* rebuild the _tracker._network

          returns a task name if the _tracker._network has changed, else None.

          kwarg 'from_user' signifies the enty is a starting target, adding cli args if necessary and linking to the root.
        """
        x : Any
        abs_name         : Maybe[TaskName_p]
        inst_name        : Concrete[TaskName_p]
        target_priority  : int  = self._tracker._declare_priority
        ##--|
        match target:
            case Artifact_i() as art:
                assert(target in self._tracker.artifacts)
                self._tracker._connect(art, None if from_user else False) # type: ignore[arg-type]
                self.active_set.add(art) # type: ignore[arg-type]
                self._queue.add(art, priority=target_priority)
                if status:
                    assert(isinstance(status, TaskStatus_e))
                    assert(hasattr(self._tracker, "set_status"))
                    self._tracker.set_status(art, status)

                assert(hasattr(self._tracker, "get_status"))
                logging.debug("[Queue] %s : %s", self._tracker.get_status(target=art), art)
                return cast("Artifact_i", art)
            case TaskName_p() | str():
                abs_name = self._queue_prep_name(target)
            case x:
                raise TypeError(type(x))

        match abs_name:
            case None:
                return None
            case TaskName_p() | str() as x if x not in self._tracker.specs:
                raise doot.errors.TrackingError("Unrecognized task name, it may not be registered", x)
            case TaskName_p() as x if not x.uuid():
                inst_name = cast("TaskName_p", self._tracker._instantiate(x)) # type: ignore[attr-defined]
            case TaskName_p() as x:
                inst_name = x

        if inst_name not in self._tracker.network:
            self._tracker._connect(inst_name, None if from_user else False) # type: ignore[attr-defined]

        self.active_set.add(inst_name)
        match self._tracker.tasks.get(inst_name, None):
            case None:
                self._queue.add(inst_name, API.DECLARE_PRIORITY)
            case x:
                self._queue.add(inst_name, x.priority)
        # Apply the override status if necessary:
        match status:
            case TaskStatus_e():
                assert(hasattr(self._tracker, "set_status"))
                self._tracker.set_status(inst_name, status)
            case None:
                assert(hasattr(self._tracker, "get_status"))
                status = self._tracker.get_status(target=inst_name)

        logging.debug("[Queue] %s (P:%s) : %s", status, target_priority, inst_name[:])
        return inst_name

    def deque_entry(self, *, peek:bool=False) -> Concrete[TaskName_p]|Artifact_i:
        """ remove (or peek) the top task from the _queue .
          decrements the priority when popped.
        """
        focus : TaskName_p|Artifact_i
        assert(hasattr(self._tracker, "get_priority"))
        assert(hasattr(self._tracker, "set_status"))
        if peek:
            return self._queue.peek()

        match self._queue.pop():
            case TaskName_p() as focus if focus not in self._tracker.tasks:
                pass
            case TaskName_p() as focus if self._tracker.get_priority(target=focus) < self._tracker._min_priority:
                logging.warning("[Deque] Halting (Min Priority) : %s", focus[:])
                self._tracker.set_status(focus, TaskStatus_e.HALTED)
            case TaskName_p() as focus:
                task  = self._tracker.tasks[focus]
                prior = task.priority
                task.priority -= 1
                logging.debug("[Deque] %s -> %s : %s", prior, task.priority, focus[:])
            case TaskArtifact() as focus: # type: ignore[misc]
                focus.priority -= 1 # type: ignore[union-attr]

        return focus

    def clear_queue(self) -> None:
        """ Remove everything from the task queue,

        """
        # TODO _queue the task's failure/cleanup tasks
        self.active_set =  set()
        self.task_queue = boltons.queueutils.HeapPriorityQueue()

    ##--| private
    def _queue_prep_name(self, name:str|TaskName_p) -> Maybe[TaskName_p]:  # noqa: PLR0911
        """ Heuristics for queueing task names

        """
        match name:
            case TaskName_p() if name == self._tracker._root_node:
                return None
            case TaskName_p() if name in self.active_set:
                return name
            case TaskName_p() if name in self._tracker.tasks:
                return name
            case TaskName_p() if name in self._tracker.network:
                return name
            case TaskName_p() if name in self._tracker.specs:
                return name
            case TaskName_p():
                raise doot.errors.TrackingError("Unrecognized queue argument provided, it may not be registered", name)
            case str():
                return self._queue_prep_name(TaskName(name))
            case _:
                return name
