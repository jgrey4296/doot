#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import warnings
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot

# ##-- end 1st party imports

doot._test_setup()

# ##-- 1st party imports
import doot._abstract
from doot.control.locations import DootLocations
from doot.structs import TaskSpec
from doot.task.check_locs import CheckLocsTask

# ##-- end 1st party imports

logging = logmod.root

class TestCheckLocsTask:

    def test_initial(self):
        doot._test_setup()
        obj = CheckLocsTask()
        assert(isinstance(obj, doot._abstract.Task_i))
