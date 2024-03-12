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
from doot.actions.job_expansion import JobExpandAction, JobMatchAction
import doot.errors
from doot.structs import DootKey, DootActionSpec, DootTaskName

class TestJobExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec.build({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": DootTaskName.build("basic")}

    def test_solo_expansion(self):
        pass

    def test_list_expansion(self):
        pass

    def test_solo_injection(self):
        pass

    def test_list_injection(self):
        pass

    def test_replacement(self):
        pass

    def test_action_base(self):
        pass

    def test_taskname_base(self):
        pass

class TestJobMatcher:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec.build({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": DootTaskName.build("basic")}

    def test_initial(self):
        pass

class TestJobGenerate:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec.build({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": DootTaskName.build("basic")}

    def test_initial(self):
        pass
