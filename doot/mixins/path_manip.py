#!/usr/bin/env python3
"""


"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

from jgdv.structs.dkey import DKey
from jgdv.mixins.path_manip import LoopControl_e, Walker_m
from jgdv.mixins.path_manip import PathManip_m as PathManip_Base

# ##-- 1st party imports
import doot
# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

MARKER : Final[str] = doot.constants.paths.MARKER_FILE_NAME
walk_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).settings.walking.ignores()
walk_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).settings.walking.halts()

class PathManip_m(PathManip_Base):

    def _is_write_protected(self, loc) -> bool:
        logmod.info("TODO: is_write_protected?")
        return False
