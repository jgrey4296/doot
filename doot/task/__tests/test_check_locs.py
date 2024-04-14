#!/usr/bin/env python3
"""

"""
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings

import pytest

import doot
doot._test_setup()
import doot._abstract
from doot.task.check_locs import CheckLocsTask
from doot.control.locations import DootLocations
from doot.structs import DootTaskSpec

logging = logmod.root

class TestCheckLocsTask:

    def test_initial(self):
        doot._test_setup()
        obj = CheckLocsTask(DootTaskSpec.build({"name": "basic"}))
        assert(isinstance(obj, doot._abstract.Task_i))
