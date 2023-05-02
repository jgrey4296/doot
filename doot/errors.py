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

class DootDirAbsent(AttributeError):
    pass
