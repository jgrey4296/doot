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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from statemachine import State, StateMachine
from statemachine.states import States

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.enums import TaskStatus_e

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end loggingw

class TaskTrackModel:

    def check_for_spec(self):
        return False

class TaskTrackMachine(StateMachine):
    """
      A Statemachine controlling the tracking of task states
    """
    # State
    _ = States.from_enum(TaskStatus_e, initial=TaskStatus_e.NAMED, final=TaskStatus_e.DEAD, use_enum_instance=True)

    # Events
    setup = (
        _.NAMED.to(_.DEAD, cond='check_for_spec')
        | _.NAMED.to(_.DECLARED)
        | _.DECLARED.to(_.DEFINED)
        | _.DEFINED.to(_.INIT)
        # | _.INIT.to.itself(internal=True)
        )

    run = (
        _.INIT.to(_.WAIT)
        # | _.WAIT.to.itself(cond=None, internal=True)
        | _.WAIT.to(_.READY)
        | _.READY.to(_.RUNNING)
        # | _.RUNNING.to.itself(cond=None, internal=True)
        | _.RUNNING.to(_.SKIPPED, cond=None)
        | _.RUNNING.to(_.HALTED,  cond=None)
        | _.RUNNING.to(_.FAILED,  cond=None)
        | _.RUNNING.to(_.SUCCESS)
        )

    disable  = _.DISABLED.from_(_.READY, _.WAIT, _.INIT, _.DECLARED, _.DEFINED, _.NAMED)
    skip     = _.SKIPPED.from_(_.READY, _.RUNNING, _.WAIT, _.INIT, _.DECLARED, _.DEFINED)
    fail     = _.FAILED.from_(_.READY, _.RUNNING, _.WAIT, _.INIT, _.DECLARED, _.DEFINED)
    halt     = _.HALTED.from_(_.READY, _.RUNNING, _.WAIT, _.INIT, _.DECLARED, _.DEFINED)
    succeed  = _.RUNNING.to(_.SUCCESS)

    complete = (
        _.TEARDOWN.from_(_.SUCCESS, _.FAILED, _.HALTED, _.SKIPPED, _.DISABLED)
        | _.TEARDOWN.to(_.DEAD)
        )

    # Composite Events
    progress = (setup | run | disable | skip | fail | halt | succeed | complete)

    # Listeners

class ArtifactMachine(StateMachine):
    """
      A statemachine of artifact
    """
    # State
    Declared    = State(initial=True)
    Stale       = State()
    ToClean     = State()
    Removed     = State()
    Exists      = State(final=True)

    progress = (
        Declared.to(Stale, cond=None)
        | Declared.to(ToClean, cond=None)
        | Declared.to(Exists)
        | Stale.to(Removed)
        | ToClean.to(Removed)
        | Removed.to(Declared)
    )


class TaskExecutionMachine(StateMachine):
    """
      Manaages the state progression of a running task
    """
    # State
    Ready    = State(initial=True)
    Finished = State(final=True)
    Check    = State()
    Setup    = State()
    Body     = State()
    Action   = State()
    Relation = State()
    Report   = State()
    Failed   = State()
    Cleanup  = State()
    Sleep    = State()

    # Events
    run = (Ready.to(Check)
        | Check.to(Setup)
        | Setup.to(Body)
        | Body.to(Report)
        | Report.to(Cleanup, cond="is_not_job")
        | Cleanup.to(Finished)
        | Report.to(Sleep)
        | Sleep.to(Finished)
        )
    action = (Body.to(Action, Relation) | Action.to(Body) | Relation.to(Body))
    fail   = (Failed.from_(Check, Setup, Body, Action, Relation, Report) | Failed.to(Cleanup))

    # Composite Events
    progress = (action | run | fail)
