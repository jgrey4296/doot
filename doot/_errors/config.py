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

from .base import DootError, UserError

class ConfigError(UserError):
    """ Although the doot config was loaded, its format was incorrect """
    general_msg = "Doot Config Error:"
    pass

class InvalidConfigError(ConfigError):
    """ Trying to read either a 'doot.toml' or task toml file,
    something went wrong.
    """
    general_msg = "Invalid Doot Config:"
    pass


class MissingConfigError(ConfigError):
    """ An expecting core config value was not found """
    general_msg = "Doot Config Error:"
    pass

class VersionMismatchError(ConfigError):
    general_msg = "Doot Version Mismatch:"
    pass
