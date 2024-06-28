#!/usr/bin/env python3
"""

"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
# import abc
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import types
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 1st party imports
from doot.mixins.enums import EnumBuilder_m, FlagsBuilder_m

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

##-- enums

class TaskStatus_e(enum.Enum):
    """
      Enumeration of the different states a task/artifact can be in.
      The state is stored in the task object itself.

      Before a task object hsa been created, the tracker
      provides the status according to what specs exist for the task name.

    """
    # Pre-Task Object Creation statuses:
    NAMED           = enum.auto() # A Name, missing a spec
    DECLARED        = enum.auto() # Abstract Spec Exists

    DEFINED         = enum.auto() # Spec has been instantiated into the dependency network
    ARTIFACT        = enum.auto() # Default artifact status.

    STALE           = enum.auto() # Artifact exists, but is too old.
    EXISTS          = enum.auto() # The path the artifact expands to exists.

    # Task Object Exists
    DISABLED        = enum.auto() # Artificial state for if a spec or task has been disabled.
    INIT            = enum.auto() # Task Object has been created.
    WAIT            = enum.auto() # Task is awaiting dependency check and pass
    READY           = enum.auto() # Dependencies are done, ready to execute/expand.
    RUNNING         = enum.auto() # Has been given to the runner, waiting for a status update.
    SKIPPED         = enum.auto() # Runner has signaled the task was skipped.
    HALTED          = enum.auto() # Task has reached minimum priority, timing out.
    FAILED          = enum.auto() # Runner has signaled Failure.
    SUCCESS         = enum.auto() # Runner has signaled success.
    TEARDOWN        = enum.auto() # Task is ready to be killed
    DEAD            = enum.auto() # Task is done.

    # Base Task uses the default to set its state on __init__

    default         = INIT

    @classmethod
    @property
    def pre_set(cls):
        return {cls.NAMED, cls.DECLARED, cls.DEFINED, cls.ARTIFACT}

    @classmethod
    @property
    def success_set(cls):
        return {cls.SUCCESS, cls.EXISTS, cls.TEARDOWN, cls.DEAD}

    @classmethod
    @property
    def fail_set(cls):
        return {cls.SKIPPED, cls.HALTED, cls.FAILED}

    @classmethod
    @property
    def artifact_set(cls):
        return {cls.ARTIFACT, cls.EXISTS, cls.HALTED, cls.FAILED}

class ActionResponse_e(EnumBuilder_m, enum.Enum):
    """
      Description of how a Action went.
    """

    SUCCEED  = enum.auto()
    FAIL     = enum.auto()
    SKIP     = enum.auto()

    # Aliases
    SUCCESS  = SUCCEED

class QueueMeta_e(EnumBuilder_m, enum.Enum):
    """ available ways a task can be activated for running
      onRegister/auto     : activates automatically when added to the task network
      reactive            : activates if an adjacent node completes

      default             : activates only if uses queues the task, or its a dependencyOf

    """

    default      = enum.auto()
    onRegister   = enum.auto()
    reactive     = enum.auto()
    reactiveFail = enum.auto()
    auto         = onRegister

class LoopControl_e(enum.Enum):
    """
      Describes how to continue an accumulating loop.
      (like walking a a tree)

    yesAnd     : is a result, and try others.
    yes        : is a result, don't try others, Finish.
    noBut      : not a result, try others.
    no         : not a result, don't try others, Finish.
    """
    yesAnd  = enum.auto()
    yes     = enum.auto()
    noBut   = enum.auto()
    no      = enum.auto()

    @classmethod
    @property
    def loop_yes_set(cls):
        return  {cls.yesAnd, cls.yes, True}

    @classmethod
    @property
    def loop_no_set(cls):
        return  {cls.no, cls.noBut, False, None}

class EdgeType_e(EnumBuilder_m, enum.Enum):
    """ Enum describing the possible edges of the task tracker's task network """

    TASK              = enum.auto() # task to task
    ARTIFACT_UP       = enum.auto() # abstract to concrete artifact
    ARTIFACT_DOWN     = enum.auto() # concrete to abstract artifact
    TASK_CROSS        = enum.auto() # Task to artifact
    ARTIFACT_CROSS    = enum.auto() # artifact to task

    default           = TASK

    @classmethod
    @property
    def artifact_edge_set(cls):
        return  {cls.ARTIFACT_UP, cls.ARTIFACT_DOWN, cls.TASK_CROSS}

class RelationMeta_e(enum.Enum):
    """
      What types+synonyms of task relation there can be,
      in the form ? {rel} Y,

      eg: cake dependsOn baking.
      or: baking requirementFor cake.
    """
    # Core:
    dependencyOf     = enum.auto()
    requirementFor   = enum.auto()

    # dependency Aliases
    dependsOn        = dependencyOf
    productOf        = dependencyOf
    pre              = dependencyOf
    dep              = dependencyOf
    after            = dependencyOf
    # Dependant aliases
    resultsIn        = requirementFor
    post             = requirementFor
    req              = requirementFor
    before           = requirementFor

    default          = dependencyOf
    # to deprecate:
    dependantOf      = requirementFor

class ExecutionPolicy_e(EnumBuilder_m, enum.Enum):
    """ How the task execution will be ordered
      PRIORITY : Priority Queue with retry, job expansion, dynamic walk of network.
      DEPTH    : No (priority,retry,jobs). basic DFS of the pre-run dependency network
      BREADTH  : No (priority,retry,jobs). basic BFS of the pre-run dependency-network

    """
    PRIORITY = enum.auto() # By Task Priority
    DEPTH    = enum.auto() # Depth First Search
    BREADTH  = enum.auto() # Breadth First Search

    default = PRIORITY
class DKeyMark_e(EnumBuilder_m, enum.Enum):
    """
      Enums for how to use/build a dkey

    """
    FREE     = enum.auto() # -> Any
    PATH     = enum.auto() # -> pl.Path
    REDIRECT = enum.auto() # -> DKey
    STR      = enum.auto() # -> str
    CODE     = enum.auto() # -> coderef
    TASK     = enum.auto() # -> taskname
    ARGS     = enum.auto() # -> list
    KWARGS   = enum.auto() # -> dict
    POSTBOX  = enum.auto() # -> list
    NULL     = enum.auto() # -> None

    default  = FREE

##-- end enums

##-- flags

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

class Report_f(enum.Flag):
    """ Flags to mark what a reporter reports
      For categorizing the most common parts of Reporting.
    """
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

    OTHER    = enum.auto()
    #

    default  = enum.auto()
##-- end flags
