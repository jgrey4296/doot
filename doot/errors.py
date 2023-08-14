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

class DootError(Exception):
    general_msg = "Non-Specific Doot Error:"

    def __str__(self):
        try:
            return self.args[0] % self.args[1:]
        except TypeError:
            return str(self.args)


class DootTaskError(DootError):
    general_msg = "Doot Task Error:"
    pass

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
class DootParseError(DootError):
    general_msg = "Doot CLI Parsing Failure:"
    pass

class DootInvalidConfig(DootError):
    general_msg = "Invalid Doot Config:"
    pass

class DootDirAbsent(DootError):
    general_msg = "Missing Directory:"
    pass

class DootPluginError(DootError):
    general_msg = "Doot Plugin Error:"
    pass

class DootCommandError(DootError):
    general_msg = "Doot Command Error:"
    pass

class DootConfigError(DootError):
    general_msg = "Doot Config Error:"
    pass
