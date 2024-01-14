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
from doot.enums import TaskFlags
from doot.structs import DootTaskSpec, TaskStub
from doot.task.base_job import DootJob
import doot._abstract

class TestBaseJob:

    def test_initial(self):
        job = DootJob(DootTaskSpec.from_dict({"name": "basic::example", "flags": ["JOB"]}))
        assert(isinstance(job, doot._abstract.TaskBase_i))
        assert(TaskFlags.JOB in job.spec.flags)

    def test_paramspecs(self):
        job = DootJob(DootTaskSpec.from_dict({"name": "basic::example"}))
        param_specs = job.param_specs
        assert(isinstance(param_specs, list))
        assert(len(param_specs) == 3)

    def test_spec(self):
        ##-- setup
        job1 = DootJob(DootTaskSpec.from_dict({"name" :"basic::example"}))
        job2 = DootJob(DootTaskSpec.from_dict({"name" :"other.group::blah"}))
        ##-- end setup
        assert(str(job1.name) == "basic::example")
        assert(str(job2.name) == "\"other.group\"::blah")
        assert(job1 != job2)
        assert(job1 == job1)

    def test_build(self):
        ##-- setup
        job = DootJob(DootTaskSpec.from_dict({"name": "basic::example"}))
        ##-- end setup

        # Run:
        tasks = list(job.build())

        ##-- check
        assert(len(tasks) == 1)
        ##-- end check
        pass

    def test_build_multi(self):
        ##-- setup
        job = DootJob(DootTaskSpec.from_dict({"name": "basic::example"}))
        ##-- end setup

        # Run:
        tasks = list(job.build())

        ##-- check
        assert(len(tasks) == 1)
        ##-- end check
        pass

    def test_class_stub(self):
        stub_obj = TaskStub(ctor=DootJob)
        stub = DootJob.stub_class(stub_obj)
        assert(isinstance(stub, TaskStub))
