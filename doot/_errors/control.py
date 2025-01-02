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

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from .base import DootError, BackendError

class ControlError(BackendError):
    pass

class TrackingError(ControlError):
    """ The underlying sequencing of task running failed in some way.  """
    general_msg = "Doot Tracking Failure:"
    pass

class TaskExecutionError(ControlError):
    """ An Error indicating a specific task failed  """
    general_msg = "Doot Task Error:"

    def __init__(self, msg, *args, task:None|"Task_i"=None):
        super().__init__(msg, *args)
        self.task = task

    @property
    def task_name(self):
        if not self.task:
            return ""
        return self.task.shortname

    @property
    def task_source(self):
        if not self.task:
            return ""
        return self.task.source

class JobExpansionError(TaskExecutionError):
    pass

class ActionCallError(TaskExecutionError):
    """ In the course of executing a task, one of it's actions failed. """
    general_msg = "Doot Action Failure:"
    pass

class ActionStateError(ActionCallError):
    """ An action required certain state to exist, but it wasn't found. """
    general_msg = "Doot Action State Fields Missing:"
    pass
