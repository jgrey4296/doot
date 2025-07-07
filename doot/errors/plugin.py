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

# ##-- Generated Exports
__all__ = ( # noqa: RUF022

# -- Classes
"AliasSearchError", "PluginError", "PluginLoadError",

)
# ##-- end Generated Exports

from ._base import DootError, BackendError

class PluginError(BackendError):
    """ In the course of starting up, doot tried to load a plugin that was bad. """
    general_msg = "Doot Plugin Error:"
    pass

class PluginLoadError(PluginError):
    pass

class AliasSearchError(PluginError):
    pass
