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
import doot.errors
from doot.structs import DKey, TaskSpec, ActionSpec, TaskName
import doot.actions.job_actions as JA

printer = logmod.getLogger("doot._printer")
logging = logmod.root

class TestJobActions:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "basic", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": TaskName.build("agroup::basic")}

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass


class TestJobWalker:
    @pytest.mark.skip
    def test_walker(self, spec, state):
        pass


class TestJobLimiter:
    @pytest.mark.skip
    def test_limiter(self, spec, state):
        pass
