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
from doot.workflow._interface import (CLI_K, MUST_INJECT_K, Artifact_i,
                                      ArtifactStatus_e, InjectSpec_i,
                                      RelationSpec_i, Task_i, Task_p,
                                      TaskName_p, TaskSpec_i, TaskStatus_e)

# ##-- end 1st party imports

# ##-| Local
from . import _interface as API # noqa: N812
from ._base import Tracker_abs
from ._interface import TaskTracker_p
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
# isort: on
# ##-- end types

##-- logging
logging    = logmod.getLogger(__name__)
##-- end logging

assert(isinstance(TrackRegistry, API.Registry_p))
##--|

@Proto(API.TaskTracker_p)
class NaiveTracker(Tracker_abs):
    """ Specific implementations for the default naive tracker """
    _registry : TrackRegistry

    def next_for(self, target:Maybe[str|TaskName_p]=None) -> Maybe[Task_p|Artifact_i]:
        """ ask for the next task that can be performed

          Returns a Task or Artifact that needs to be executed or created
          Returns None if it loops too many times trying to find a target,
          or if theres nothing left in the queue

        """
        count   : int
        focus   : TaskName_p|Artifact_i
        idx     : int
        result  : Maybe[Task_p|Artifact_i]
        status  : TaskStatus_e|ArtifactStatus_e
        x       : Any

        logging.info("[Next.For] (Active: %s)", len(self.active))
        if not self.is_valid:
            raise doot.errors.TrackingError("Network is in an invalid internal_state")

        if target and target not in self.active:
            self.queue(target, silent=True)

        idx, count  = 0, API.MAX_LOOP
        result      = None
        while (result is None) and bool(self._queue) and 0 < (count:=count-1) and (idx:=idx+1):
            focus      = self._deque()
            status, _  = self.get_status(target=focus)
            logging.debug("[Next.For.%-3s]: %s  : %s", idx, status, focus)

            match focus:
                case x if x not in self.active:
                    continue
                case TaskName_p():
                    result = self._next_for_task(focus)
                case Artifact_i():
                    result = self._next_for_artifact(focus)
                case x: # Error otherwise
                    raise doot.errors.TrackingError("Unknown task focus", x)

        else:
            logging.info("[Next.For] <- %s", result)
            return result

    def _next_for_task(self, focus:TaskName_p) -> Maybe[Task_p]:  # noqa: PLR0912, PLR0915
        """ logic for handling a dequed task """
        x : Any
        status, _ = self.get_status(target=focus) # type: ignore[attr-defined]
        match status:
            case TaskStatus_e.DEAD:
                # Clear internal_state
                self.specs[focus].task = TaskStatus_e.DEAD
                self.active.remove(focus)
                assert(focus not in self.active)
            case TaskStatus_e.DISABLED:
                self.active.remove(focus)
            case TaskStatus_e.TEARDOWN:
                # Queue cleanup tasks
                for succ, _ in self._successor_states_of(focus):
                    match self.queue(succ):
                        case TaskName() as x if x.is_cleanup():
                            # make the cleanup task early, to apply shared internal_state
                            assert(isinstance(focus, TaskName))
                            self._instantiate(x, parent=focus, task=True)
                        case _:
                            pass
                else:
                    # TODO for cleanup succ, move focus.internal_state -> succ.internal_state
                    self.set_status(focus, TaskStatus_e.DEAD) # type: ignore[attr-defined]
            case TaskStatus_e.SUCCESS:
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
                return cast("Task_p", self.specs[focus].task)
            case TaskStatus_e.WAIT: # Add dependencies of a task to the stack
                waiting  : bool  = False
                deps_of_focus    = self._dependency_states_of(focus)
                for dep, dep_status in deps_of_focus:
                    if dep_status in API.SUCCESS_STATUSES:
                        continue
                    self.queue(dep)
                    waiting = True
                else:
                    match waiting:
                        case False:
                            self.queue(focus, status=TaskStatus_e.READY)
                        case True:
                            logging.debug("[Next.For] Task Blocked: %s on : %s", focus, deps_of_focus)
                            self.queue(focus)
            case TaskStatus_e.INIT:
                self.queue(focus, status=TaskStatus_e.WAIT)
            case TaskStatus_e.DEFINED:
                self._instantiate(focus, task=True)
                self.queue(focus)
            case TaskStatus_e.DECLARED:
                self.queue(focus, status=TaskStatus_e.DEFINED)
            case TaskStatus_e.NAMED:
                logging.warning("A Name only was queued, it has no backing in the tracker: %s", focus)
            case x: # Error otherwise
                raise doot.errors.TrackingError("Unknown task internal_state", x)
        ##--|
        return None

    def _next_for_artifact(self, focus:Artifact_i) -> Maybe[Artifact_i]:  # noqa: PLR0912
        """ logic for handling a dequed artifact """
        status, _ = self.get_status(target=focus) # type: ignore[attr-defined]
        match status:
            case ArtifactStatus_e.EXISTS:
                # TODO artifact Exists, queue its dependents and *don't* add the artifact back in
                pass
            case ArtifactStatus_e.STALE:
                for pred, _ in self._dependency_states_of(focus):
                    self.queue(pred)
            case ArtifactStatus_e.DECLARED if bool(focus):
                self.queue(focus)
            case ArtifactStatus_e.DECLARED: # Add dependencies of an artifact to the stack
                deps : list[tuple] = self._dependency_states_of(focus)
                match deps:
                    case [] if not focus.is_concrete():
                        self.queue(focus)
                    case []:
                        assert(not bool(focus))
                        path = doot.locs[focus]
                        # Returns the artifact, the runner can try to create
                        # it, then override the halt
                        return focus
                    case [*xs]:
                        logging.info("[Next.For] Artifact Blocked, queuing producer tasks, count: %s", len(xs))
                    case x:
                        raise TypeError(type(x))

                for dep, dep_state in deps:
                    if dep_state in API.SUCCESS_STATUSES:
                        continue
                    self.queue(dep)
                else:
                    # No need to requeue, as tasks will check for the artifacts themselves
                    pass

            case x: # Error otherwise
                raise doot.errors.TrackingError("Unknown task internal_state", x)

        ##--|
        return None

    @override
    def _instantiate(self, target:TaskName_p|RelationSpec_i, *args:Any, task:bool=False, **kwargs:Any) -> Maybe[TaskName_p]:
        """ extends base instantiation to add late injection for tasks """
        parent : TaskName_p
        result : Maybe[TaskName_p]
        ##--|
        parent  = kwargs.pop("parent", None)
        match super()._instantiate(target, *args, task=task, **kwargs):
            case TaskName_p() as result if task:
                self._apply_injections(result, parent=parent)
            case result:
                pass

        return result

    ##--| internal

    def _dependency_states_of(self, focus:TaskName_p|Artifact_i) -> list[tuple]:
        return [(x, self.get_status(target=x)[0]) for x in self._network.pred[focus]]

    def _successor_states_of(self, focus:TaskName_p|Artifact_i) -> list[tuple]:
        return [(x, self.get_status(target=x)[0]) for x in self._network.succ[focus]]

    def _deque(self) -> TaskName_p|Artifact_i:
        focus = self._queue.deque_entry()
        match self.specs.get(focus, focus): # type: ignore[arg-type]
            case None | API.SpecMeta_d(task=None) | TaskName_p():
                pass
            case API.SpecMeta_d(task=Task_p() as task) if task.priority < self._min_priority:
                logging.warning("[Deque] Halting (Min Priority) : %s", focus[:])
                self.set_status(focus, TaskStatus_e.HALTED)
            case API.SpecMeta_d(task=Task_p() as task):
                prior         = task.priority
                task.priority = 1
                logging.debug("[Deque] %s -> %s : %s", prior, task.priority, focus[:])
            case TaskArtifact() as focus: # type: ignore[misc]
                focus.priority -= 1 # type: ignore[union-attr]

        return focus

    ##--| utils

    def get_status(self, *, target:Maybe[Concrete[TaskName_p]|Artifact_i]=None) -> tuple[TaskStatus_e|ArtifactStatus_e, int]:
        return self._registry.get_status(target)

    def set_status(self, task:Concrete[TaskName_p]|Artifact_i|Task_p, internal_state:TaskStatus_e) -> bool:
        return self._registry.set_status(task, internal_state) # type: ignore[attr-defined]

    def _apply_injections(self, name:TaskName_p, *, parent:Maybe[TaskName_p]=None) -> None:
        """ After a task is created, values can be injected into it.
        these include, in order:
        - parent internal_state,
        - cli params
        - instantiator internal_state injection
        """
        x            : Any
        meta         : API.SpecMeta_d
        task         : Task_p
        idx          : int = 0
        ##--|
        match self.specs[name]:
            case API.SpecMeta_d(task=Task_p() as task) as meta:
                pass
            case x:
                raise TypeError(type(x))
        ##--| Get parent data (for cleanup tasks
        match self._get_parent_data(parent):
            case None:
                pass
            case dict() as pdata:
                task.internal_state.update(pdata)
        ##--| apply CLI params
        match self._get_cli_data(name):
            case None:
                pass
            case dict() as cdata:
                # Apply CLI passed params, but only as the default
                # So if override values have been injected, they are preferred
                for x,y in cdata.items():
                    task.internal_state.setdefault(x, y)

        ##--| apply late injections
        match self._get_inject_data(name):
            case None:
                pass
            case dict() as idata:
                task.internal_state.update(idata)

        ##--| validate
        if CLI_K in task.internal_state: # type: ignore[attr-defined]
            del task.internal_state[CLI_K] # type: ignore[attr-defined]
        match task.spec.extra.on_fail([])[MUST_INJECT_K](): # type: ignore[attr-defined]
            case []:
                pass
            case [*xs] if bool(missing:=[x for x in xs if x not in task.internal_state]): # type: ignore[attr-defined]
                raise doot.errors.TrackingError("Task did not receive required injections", task.name, xs, task.internal_state.keys()) # type: ignore[attr-defined]

        ##--| prep actions
        task.prepare_actions()

    def _get_parent_data(self, parent:Maybe[TaskName_p]=None) -> Maybe[dict]:
        match self.specs.get(parent, None): # type: ignore[arg-type]
            case None:
                return None
            case API.SpecMeta_d(task=Task_p() as p_task):
                return dict(p_task.internal_state)

    def _get_cli_data(self, name:TaskName_p) -> Maybe[dict]:
        idx = 0
        target = name.pop()[:,:]
        return doot.args.on_fail({}).subs[target][idx]['args']()

    def _get_inject_data(self, name:TaskName_p) -> Maybe[dict]:
        inj_control  : TaskName_p
        inj          : InjectSpec_i
        meta  = self.specs[name]

        match meta.injection_source:
            case None:
                inj_control = None
            case TaskName_p() as inj_control, _ if inj_control not in self.specs:
                raise ValueError("Late Injection source is not a task", inj_control)
            case TaskName_p() as inj_control, InjectSpec_i() as inj:
                pass

        match self.specs.get(inj_control, None): # type: ignore[arg-type]
            case None:
                return None
            case API.SpecMeta_d(task=Task_p() as control):
                return inj.apply_from_state(control)
            case x:
                raise TypeError(type(x))
