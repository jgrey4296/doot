#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

__all__ = ["DootError", "DootTaskError", "DootTaskLoadError", "DootTaskFailed", "DootTaskTrackingError", "DootTaskInterrupt"
           "DootParseError", "DootInvalidConfig", "DootLocationError", "DootLocationExpansionError", "DootDirAbsent",
           "DootPluginError", "DootCommandError", "DootConfigError"]

class DootError(Exception):
    """
      The base class for all Doot Errors
      will try to % format the first argument with remaining args in str()
    """
    general_msg = "Non-Specific Doot Error:"

    def __str__(self):
        try:
            return self.args[0] % self.args[1:]
        except TypeError:
            return str(self.args)

class DootTaskError(DootError):
    general_msg = "Doot Task Error:"

    def __init__(self, msg, *args, task=None):
        super().__init__(msg, *args)
        self.task = task

    @property
    def task_name(self):
        if not self.task:
            return ""
        return str(self.task.name)

    @property
    def task_source(self):
        if not self.task:
            return ""
        return self.task.source

class DootTaskLoadError(DootTaskError):
    general_msg = "Doot Task Load Failure:"
    pass

class DootTaskFailed(DootTaskError):
    general_msg = "Doot Task Failure:"
    pass

class DootTaskTrackingError(DootTaskError):
    general_msg = "Doot Tracking Failure:"
    pass

class DootTaskInterrupt(DootTaskError):
    pass

class DootActionError(DootTaskError):
    general_msg = "Doot Action Failure:"
    pass

class DootActionStateError(DootActionError):
    general_msg = "Doot Action State Fields Missing:"
    pass

class DootParseError(DootError):
    general_msg = "Doot CLI Parsing Failure:"
    pass

class DootParseResetError(DootParseError):
    pass

class DootInvalidConfig(DootError):
    general_msg = "Invalid Doot Config:"
    pass

class DootLocationError(DootError):
    general_msg = "Location Error:"

class DootLocationExpansionError(DootLocationError):
    general_msg = "Expansion of Location hit max value:"

class DootDirAbsent(DootError):
    general_msg = "Missing Directory:"

class DootPluginError(DootError):
    general_msg = "Doot Plugin Error:"
    pass

class DootCommandError(DootError):
    general_msg = "Doot Command Error:"
    pass

class DootConfigError(DootError):
    general_msg = "Doot Config Error:"
    pass

class DootMissingConfigError(DootError):
    general_msg = "Doot Config Error:"
    pass

class DootEarlyExit(Exception):
    pass

class DootKeyError(DootError):
    pass
