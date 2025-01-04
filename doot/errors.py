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

# ##-- 1st party imports
from doot._errors.base import DootError, BackendError, FrontendError, UserError
from doot._errors.command import CommandError
from doot._errors.config import ConfigError, InvalidConfigError, MissingConfigError, VersionMismatchError
from doot._errors.control import (ActionCallError, ActionStateError,
                                  ControlError, TaskExecutionError,
                                  TrackingError)
from doot._errors.parse import ParseError
from doot._errors.plugin import AliasSearchError, PluginError, PluginLoadError
from doot._errors.state import (StateError, InjectionError, KeyAccessError,
                                KeyExpansionError, GlobalStateMismatch,
                                LocationError)
from doot._errors.struct import StructError, StructLoadError
from doot._errors.task import TaskError, TaskFailed, TaskTrackingError, ActionError

# ##-- end 1st party imports


class EarlyExit(Exception):
    """ Doot was instructed to shut down before completing the requested comand """
    pass

class Interrupt(ControlError):
    """ A Task was interrupted, usually to drop into a debugger """
    pass

class TaskFailed(TaskExecutionError):
    """ A Task attempted to run, but failed in some way. """
    general_msg = "Doot Task Failure:"
    pass
