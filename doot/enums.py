#!/usr/bin/env python3
"""
These are the core enums and flags used to easily convey information around doot.
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import enum
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)

# ##-- end stdlib imports

# ##-- 1st party imports
from doot.mixins.enums import EnumBuilder_m, FlagsBuilder_m
from doot._abstract.control import ExecutionPolicy_e, QueueMeta_e, EdgeType_e
from doot._abstract.task import TaskStatus_e, ActionResponse_e
from doot._abstract.reporter import Report_f
from doot._abstract.key import DKeyMark_e
# ##-- end 1st party imports

class RelationMeta_e(enum.Enum):
    """
      What types+synonyms of task relation there can be,
      in the form Obj {rel} Y,

      eg: cake dependsOn baking.
      or: baking requirementFor cake.
      or: eatingCake conflictsWith givingCake
    """
    needs            = enum.auto()
    blocks           = enum.auto()
    # excludes         = enum.auto()

    default          = needs

##-- flags

class LocationMeta_f(FlagsBuilder_m, enum.Flag):
    """ Available metadata attachable to a location """

    abstract     = enum.auto()
    artifact     = enum.auto()
    directory    = enum.auto()
    cleanable    = enum.auto()
    normOnLoad   = enum.auto()
    protected    = enum.auto()
    glob         = enum.auto()
    expandable   = enum.auto()
    remote       = enum.auto()

    # Aliases
    file         = artifact
    location     = directory
    indefinite   = abstract

    default      = directory

class TaskMeta_f(FlagsBuilder_m, enum.Flag):
    """
      Flags describing properties of a task,
      stored in the Task_i instance itself.
    """

    TASK         = enum.auto()
    JOB          = enum.auto()
    TRANSFORMER  = enum.auto()

    INTERNAL     = enum.auto()
    JOB_HEAD     = enum.auto()
    CONCRETE     = enum.auto()
    DISABLED     = enum.auto()

    EPHEMERAL    = enum.auto()
    IDEMPOTENT   = enum.auto()
    REQ_TEARDOWN = enum.auto()
    REQ_SETUP    = enum.auto()
    IS_TEARDOWN  = enum.auto()
    IS_SETUP     = enum.auto()
    THREAD_SAFE  = enum.auto()
    STATEFUL     = enum.auto()
    STATELESS    = enum.auto()
    VERSIONED    = enum.auto()

    default      = TASK

##-- end flags
