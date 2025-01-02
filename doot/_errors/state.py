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

class StateError(BackendError):
    pass

class KeyAccessError(StateError):
    """ A failure occurred while accessing task state using a key. """
    pass

class KeyExpansionError(StateError):
    """ For failures to access, expand, or constraint state keys """
    pass

class InjectionError(StateError):
    pass

class LocationError(StateError):
    pass

class GlobalStateMismatch(StateError):
    pass
