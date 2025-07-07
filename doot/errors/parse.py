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
"ParseError",

)
# ##-- end Generated Exports

from ._base import DootError, BackendError

class ParseError(BackendError):
    """ In the course of parsing CLI input, a failure occurred. """
    general_msg = "Doot CLI Parsing Failure:"
    pass
