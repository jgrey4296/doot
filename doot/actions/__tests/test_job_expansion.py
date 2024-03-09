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

logging = logmod.root

import doot
doot._test_setup()
from doot.actions.job_expansion import JobInjector
import doot.errors
from doot.structs import DootKey, DootActionSpec, DootTaskName

class TestJobExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec.from_data({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": DootTaskName.from_str("basic")}

class TestJobMatcher:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec.from_data({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": DootTaskName.from_str("basic")}

class TestJobGenerate:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec.from_data({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": DootTaskName.from_str("basic")}
