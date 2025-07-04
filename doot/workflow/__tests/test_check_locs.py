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


# ##-- 1st party imports
from .._interface import Task_p
from ..structs.task_spec import TaskSpec
from ..check_locs import CheckLocsTask
from doot.util.testing_fixtures import wrap_locs
# ##-- end 1st party imports

logging = logmod.root

@pytest.mark.skip
class TestCheckLocsTask:

    def test_initial(self, wrap_locs):
        obj = CheckLocsTask()
        assert(isinstance(obj, Task_p))


    @pytest.mark.skip
    def test_todo(self):
        pass
