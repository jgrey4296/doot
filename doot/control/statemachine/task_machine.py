#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
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

from statemachine import StateMachine, State

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import doot

class TaskTrackModel:

    def check_for_spec(self, machine):
        return True

    def

class TaskTrackMachine(StateMachine):
    """
      A Statemachine controlling the tracking of task states
    """
    # States
    # TODO possibly use States.from_enum(TaskStatus_e, initial=TaskStatus_e.NAMED, final=TaskStatus_e.DEAD)
    Named       = State(initial=True)
    Dead        = State(final=True)

    Declared    = State()

    Defined     = State()

    Initialised = State()
    Wait        = State()
    Ready       = State()
    Running     = State()

    Disabled    = State()
    Skipped     = State()
    Halted      = State()
    Failed      = State()
    Success     = State()
    Teardown    = State()

    # Events
    setup = (
        Named.to(Dead, cond="check_for_spec")
        | Named.to(Declared)
        | Declared.to(Defined)
        | Defined.to(Initialised)
        )

    run = (
        Initialised.to(Wait)
        | Wait.to.itself(cond=None)
        | Wait.to(Ready)
        | Ready.to(Running)
        | Running.to.itself(cond=None)
        | Running.to(Skipped, cond=None)
        | Running.to(Halted,  cond=None)
        | Running.to(Failed,  cond=None)
        | Running.to(Success)
        )

    disable  = Disabled.from_(Ready, Wait, Initialised, Declared, Defined, Named)
    skip     = Skipped.from_(Ready, Running, Wait, Initialised, Declared, Defined)
    fail     =  Failed.from_(Ready, Running, Wait, Initialised, Declared, Defined)
    halt     =  Halted.from_(Ready, Running, Wait, Initialised, Declared, Defined)
    succeed  = Running.to(Success)

    complete = (
        Teardown.from_(Success, Failed, Halted, Skipped, Disabled)
        | Teardown.to(Dead)
        )

    # Composite Events
    progress = (setup | run | disable | skip | fail | halt | succeed | complete)

    # Listeners

class TaskExecutionMachine(StateMachine):
    """
      Manaages the state progression of a running task
    """
    # States
    Ready    = State(initial=True)
    Finished = State(final=True)
    Test     = State()
    Setup    = State()
    Body     = State()
    Action   = State()
    Relation = State()
    Report   = State()
    Failed   = State()
    Cleanup  = State()
    Sleep    = State()

    # Events
    run = (Ready.to(Test)
        | Test.to(Setup)
        | Setup.to(Body)
        | Body.to(Report)
        | Report.to(Cleanup, cond="is_not_job")
        | Cleanup.to(Finshed)
        | Report.to(Sleep)
        | Sleep.to(Finished)
        )
    action = (Body.to(Action, Relation) | Action.to(Body) | Relation.to(Body))
    fail   = (Failed.from_(Test, Setup, Body, Action, Relation, Report) | Failed.to(Cleanup))

    # Composite Events
    progress = (action | run | fail)

class JobMachine(StateMachine):
    """
      A Modifed statemachine of jobs
    """
    # States
    todo   = State(initial=True)
    finish = State(final=True)

    go     = todo.to(finish)

class ArtifactMachine(StateMachine):
    """
      A statemachine of artifact
    """
    # States
    Declared  = State(initial=True)
    Dead      = State(final=True)
    # Disabled  = State()
    # Stale     = State()
    # Exists    = State()
    # Teardown  = State()

    go = Declared.to(Dead)
