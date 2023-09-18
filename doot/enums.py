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

class TaskStateEnum(enum.Enum):
    """
      Enumeration of the different states a task can be in.
      The state is stored in a TaskTracker_i
    """
    TEARDOWN        = enum.auto()
    SUCCESS         = enum.auto()
    FAILED          = enum.auto()
    HALTED          = enum.auto()
    WAIT            = enum.auto()
    READY           = enum.auto()
    EXISTS          = enum.auto()
    INIT            = enum.auto()
    DEFINED         = enum.auto()
    DECLARED        = enum.auto()
    ARTIFACT        = enum.auto()

class TaskFlags(enum.Flag):
    """
      Flags describing properties of a task,
      stored in the Task_i instance itself.
    """
    TASK         = enum.auto()
    TASKER       = enum.auto()
    EPHEMERAL    = enum.auto()
    IDEMPOTENT   = enum.auto()
    REQ_TEARDOWN = enum.auto()
    REQ_SETUP    = enum.auto()
    IS_TEARDOWN  = enum.auto()
    IS_SETUP     = enum.auto()
    THREAD_SAFE  = enum.auto()
    STATEFUL     = enum.auto()
    STATELESS    = enum.auto()

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
    TASKER   = enum.auto()
    ACTION   = enum.auto()
    CONFIG   = enum.auto()

class StructuredNameEnum(enum.Enum):
    """ What a structured name describes """
    TASK     = enum.auto()
    CLASS    = enum.auto()
    CALLABLE = enum.auto()
