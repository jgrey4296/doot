#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN202, B011
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings

import pytest

import doot
from doot.workflow._interface import TaskMeta_e
from doot.workflow import TaskSpec, DootJob
from doot.cmds.structs import TaskStub
from .. import _interface as API  # noqa: N812

logging = logmod.root

class TestBaseJob:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133


    def test_ctor(self):
        match DootJob:
            case API.Task_p():
                assert(True)
            case x:
                assert(False), x
        match DootJob:
            case API.Job_p():
                assert(True)
            case x:
                assert(False), x

    def test_initial(self):
        spec = TaskSpec.build({"name": "basic::example", "meta": ["JOB"]})
        assert(TaskMeta_e.JOB in spec.meta)
        match DootJob(spec):
            case API.Job_p():
                assert(True)
            case x:
                 assert(False), x

    def test_param_specs(self):
        job = DootJob(TaskSpec.build({"name": "basic::example"}))
        param_specs = job.param_specs()
        assert(isinstance(param_specs, list))
        assert(len(param_specs) == 3)

    def test_spec(self):
        job1 = DootJob(TaskSpec.build({"name" :"basic::example"}))
        job2 = DootJob(TaskSpec.build({"name" :"other.group::blah"}))
        assert(str(job1.name) == "basic::example")
        assert(str(job2.name) == "other.group::blah")
        assert(job1 != job2)

    def test_class_stub(self):
        stub_obj = TaskStub(ctor=DootJob)
        stub = DootJob.stub_class(stub_obj)
        assert(isinstance(stub, TaskStub))

    @pytest.mark.skip
    def test_todo(self):
        pass
