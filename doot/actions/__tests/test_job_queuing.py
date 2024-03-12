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
from doot.actions.job_queuing import JobQueueAction, JobQueueHead, JobChainer
import doot.errors
from doot.structs import DootKey, DootActionSpec, DootTaskName

class TestJobQueue:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec.build({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": DootTaskName.build("basic")}

    def test_initial(self, spec, state):
        obj = JobQueueAction()
        result = obj(spec, state)
        assert(isinstance( result, list ))

    def test_from_arg(self, spec, state):
        obj = JobQueueAction()
        result = obj(spec, state)
        assert(isinstance( result, list ))

    def test_from_multi_arg(self):
        pass

    def test_args(self):
        pass

class TestJobQueueHead:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec.build({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": DootTaskName.build("basic")}

    def test_initial(self):
        pass

class TestJobChainer:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec.build({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": DootTaskName.build("basic")}

    def test_initial(self):
        pass
