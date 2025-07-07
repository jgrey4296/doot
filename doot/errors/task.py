#!/usr/bin/env python3
"""
These are the doot specific errors that can occur
"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)

# ##-- end stdlib imports

from ._base import DootError, BackendError

if TYPE_CHECKING:
    from jgdv import Maybe
    from doot.workflow._interface import Task_i, TaskName_p, Artifact_i, TaskSpec_i

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# ##-- Generated Exports
__all__ = ( # noqa: RUF022

# -- Classes
"ActionError", "ActionStateError", "TaskError", "TaskFailed", "TaskTrackingError",

)
# ##-- end Generated Exports

class TaskError(BackendError):
    """ An Error indicating a specific task failed  """
    task : Maybe

    general_msg = "Doot Task Error:"

    def __init__(self, msg:str, *args:Any, task:Maybe[Task_i|TaskSpec_i]=None):
        super().__init__(msg, *args)
        self.task = task

class TaskFailed(TaskError):  # noqa: N818
    """ A Task attempted to run, but failed in some way. """
    general_msg = "Doot Task Failure:"
    pass

class TaskTrackingError(TaskError):
    """ The underlying sequencing of task running failed in some way.  """
    general_msg = "Doot Tracking Failure:"
    pass

class ActionError(TaskError):
    """ In the course of executing a task, one of it's actions failed. """
    general_msg = "Doot Action Failure:"
    pass

class ActionStateError(ActionError):
    """ An action required certain state to exist, but it wasn't found. """
    general_msg = "Doot Action State Fields Missing:"
    pass
