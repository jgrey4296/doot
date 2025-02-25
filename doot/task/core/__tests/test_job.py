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
from doot.enums import TaskMeta_e
from doot.structs import TaskSpec, TaskStub
from doot.task.core.job import DootJob
import doot._abstract

class TestBaseJob:

    def test_initial(self):
        spec = TaskSpec.build({"name": "basic::example", "meta": ["JOB"]})
        assert(TaskMeta_e.JOB in spec.meta)
        match DootJob(spec):
            case doot._abstract.Job_p():
                assert(True)
            case x:
                 assert(False), x

    def test_paramspecs(self):
        job = DootJob(TaskSpec.build({"name": "basic::example"}))
        param_specs = job.param_specs
        assert(isinstance(param_specs, list))
        assert(len(param_specs) == 3)

    def test_spec(self):
        ##-- setup
        job1 = DootJob(TaskSpec.build({"name" :"basic::example"}))
        job2 = DootJob(TaskSpec.build({"name" :"other.group::blah"}))
        ##-- end setup
        assert(str(job1.name) == "basic::example")
        assert(str(job2.name) == "other.group::blah")
        assert(job1 != job2)
        assert(job1 == job1)

    def test_class_stub(self):
        stub_obj = TaskStub(ctor=DootJob)
        stub = DootJob.stub_class(stub_obj)
        assert(isinstance(stub, TaskStub))


    @pytest.mark.skip
    def test_todo(self):
        pass
