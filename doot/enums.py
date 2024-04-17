#!/usr/bin/env python3
"""

"""

##-- builtin imports
from __future__ import annotations

# import abc
import enum
import logging as logmod
import types
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)

##-- end builtin imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot.mixins.enums import EnumBuilder_m, FlagsBuilder_m

class TaskStateEnum(enum.Enum):
    """
      Enumeration of the different states a task can be in.
      The state is stored in a TaskTracker_i, not the task itself
    """
    TEARDOWN        = enum.auto()
    SUCCESS         = enum.auto()
    FAILED          = enum.auto()
    HALTED          = enum.auto()
    WAIT            = enum.auto()
    READY           = enum.auto()
    RUNNING         = enum.auto()
    EXISTS          = enum.auto()
    INIT            = enum.auto()

    SKIPPED         = enum.auto()
    DEFINED         = enum.auto()
    DECLARED        = enum.auto()
    ARTIFACT        = enum.auto()

class TaskFlags(FlagsBuilder_m, enum.Flag):
    """
      Flags describing properties of a task,
      stored in the Task_i instance itself.
    """

    default      = enum.auto()
    TASK         = enum.auto()
    JOB          = enum.auto()
    EPHEMERAL    = enum.auto()
    IDEMPOTENT   = enum.auto()
    REQ_TEARDOWN = enum.auto()
    REQ_SETUP    = enum.auto()
    IS_TEARDOWN  = enum.auto()
    IS_SETUP     = enum.auto()
    THREAD_SAFE  = enum.auto()
    STATEFUL     = enum.auto()
    STATELESS    = enum.auto()
    INTERNAL     = enum.auto()

class ReportEnum(enum.Flag):
    """ Flags to mark what a reporter reports """
    INIT     = enum.auto()
    SUCCEED  = enum.auto()
    FAIL     = enum.auto()
    EXECUTE  = enum.auto()
    SKIP     = enum.auto()

    STALE    = enum.auto()
    CLEANUP  = enum.auto()

    STATUS   = enum.auto()

    PLUGIN   = enum.auto()
    TASK     = enum.auto()
    JOB      = enum.auto()
    ACTION   = enum.auto()
    CONFIG   = enum.auto()
    ARTIFACT = enum.auto()

class ActionResponseEnum(EnumBuilder_m, enum.Enum):

    SUCCEED  = enum.auto()
    FAIL     = enum.auto()
    SKIP     = enum.auto()
    SUCCESS  = SUCCEED

class LoopControl(enum.Enum):
    """
      A Simple enum to descrbe results for testing in a maybe recursive loop
      (like walking a a tree)

    accept  : is a result, and descend if recursive
    keep    : is a result, don't descend
    discard : not a result, descend
    reject  : not a result, don't descend
    """
    yesAnd  = enum.auto()
    yes     = enum.auto()
    noBut   = enum.auto()
    no      = enum.auto()

class LocationMeta(FlagsBuilder_m, enum.Flag):
    """ Available metadata attachable to a location """

    location     = enum.auto()
    artifact     = enum.auto()
    protected    = enum.auto()
    indefinite   = enum.auto()
    cleanable    = enum.auto()
    normOnLoad   = enum.auto()

    file         = artifact
    default      = location

class TaskQueueMeta(EnumBuilder_m, enum.Enum):
    """ available ways a task can be activated for running
      onRegister/auto     : activates automatically when added to the task network
      reactive            : activates if an adjacent node completes

      default             : activates only if uses queues the task, or its a dependency

    """

    default      = enum.auto()
    onRegister   = enum.auto()
    reactive     = enum.auto()
    reactiveFail = enum.auto()
    auto         = onRegister
