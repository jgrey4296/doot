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
from ._base import DootError, BackendError, FrontendError, UserError
from .command import CommandError
from .config import ConfigError, InvalidConfigError, MissingConfigError, VersionMismatchError
from .control import (ActionCallError, ActionStateError,
                      ControlError, TaskExecutionError,
                      TrackingError)
from .parse import ParseError
from .plugin import AliasSearchError, PluginError, PluginLoadError
from .state import (StateError, InjectionError, KeyAccessError,
                    KeyExpansionError, GlobalStateMismatch,
                    LocationError)
from .struct import StructError, StructLoadError
from .task import TaskError, TaskFailed, TaskTrackingError, ActionError

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
