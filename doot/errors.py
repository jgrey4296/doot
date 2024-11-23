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

class DootTaskLoadError(DootTaskError):
    """ An error indicating a task could not be loaded correctly from its TOML spec """
    general_msg = "Doot Task Load Failure:"
    pass

class DootTaskFailed(DootTaskError):
    """ A Task attempted to run, but failed in some way. """
    general_msg = "Doot Task Failure:"
    pass

class DootTaskTrackingError(DootTaskError):
    """ The underlying sequencing of task running failed in some way.  """
    general_msg = "Doot Tracking Failure:"
    pass

class DootTaskInterrupt(DootTaskError):
    """ A Task was interrupted, usually to drop into a debugger """
    pass

class DootActionError(DootTaskError):
    """ In the course of executing a task, one of it's actions failed. """
    general_msg = "Doot Action Failure:"
    pass

class DootActionStateError(DootActionError):
    """ An action required certain state to exist, but it wasn't found. """
    general_msg = "Doot Action State Fields Missing:"
    pass

class DootParseError(DootError):
    """ In the course of parsing CLI input, a failure occurred. """
    general_msg = "Doot CLI Parsing Failure:"
    pass

class DootParseResetError(DootParseError):
    pass

class DootInvalidConfig(DootError):
    """ Trying to read either a 'doot.toml' or task toml file,
    something went wrong.
    """
    general_msg = "Invalid Doot Config:"
    pass

class DootLocationError(DootError):
    """ A Task tried to access a location that didn't existing """
    general_msg = "Location Error:"

class DootLocationExpansionError(DootLocationError):
    """ When trying to resolve a location, something went wrong. """
    general_msg = "Expansion of Location hit max value:"

class DootDirAbsent(DootError):
    """ In the course of startup verification, a directory was not found """
    general_msg = "Missing Directory:"

class DootPluginError(DootError):
    """ In the course of starting up, doot tried to load a plugin that was bad. """
    general_msg = "Doot Plugin Error:"
    pass

class DootCommandError(DootError):
    """ A Command front end failed (rather than doot's backend) """
    general_msg = "Doot Command Error:"
    pass

class DootConfigError(DootError):
    """ Although the doot config was loaded, its format was incorrect """
    general_msg = "Doot Config Error:"
    pass

class DootMissingConfigError(DootError):
    """ An expecting core config value was not found """
    general_msg = "Doot Config Error:"
    pass

class DootEarlyExit(Exception):
    """ Doot was instructed to shut down before completing the requested comand """
    pass

class DootKeyError(DootError):
    """ A failure occurred while accessing task state using a key. """
    pass

class DootStateError(DootError):
    """ For failures to access, expand, or constraint state keys """
    pass
