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
from doot.enums import TaskFlags
from doot.structs import DootTaskSpec, TaskStub, DootCodeReference
from doot.task.base_job import DootJob
from doot.mixins.job.subtask import SubTask_M
import doot._abstract

sub_ref   = DootCodeReference.build("doot.task.base_job:DootJob").add_mixins("doot.mixins.job.subtask:SubTask_M")
SubJob = sub_ref.try_import()

class SimpleSubJob(SubJob):

    def _build_subs(self):
        yield DootTaskSpec(name=self.fullname.subtask("first"))
        yield DootTaskSpec(name=self.fullname.subtask("second"))

    def alt_subgen(self):
        yield DootTaskSpec(name=self.fullname.subtask("alt_first"))
        yield DootTaskSpec(name=self.fullname.subtask("alt_second"))

class SetupTearDownJob(SimpleSubJob):

    def make(self, **kwargs):
        head     = self._build_head()
        setup    = DootTaskSpec(name=self.fullname.subtask("setup"))
        teardown = DootTaskSpec(name=self.fullname.subtask("teardown"))
        head.depends_on.append(teardown)
        head.depends_on.append(setup)

        for sub in super()._build_subs():
            sub.depends_on.append(setup.name)
            teardown.depends_on.append(sub.name)
            yield sub

        yield setup
        yield teardown
        yield head

class TestSubtasks:

    def test_initial(self):
        obj = SimpleSubJob(DootTaskSpec.build({"name": "simple"}))
        assert(isinstance(obj, doot._abstract.TaskBase_i))


    def test_custom_subgen(self):
        obj = SimpleSubJob(DootTaskSpec.build({"name": "simple", "sub_generator": SimpleSubJob.alt_subgen }))
        assert(isinstance(obj, doot._abstract.TaskBase_i))
        tasks = [x for x in obj.make() if x is not None]
        assert(len(tasks) == 3)
        names = [str(x.name) for x in tasks]
        assert("default::simple.$head$" in names)
        assert("default::simple.alt_first" in names)
        assert("default::simple.alt_second" in names)

    def test_builds_task(self):
        obj   = SimpleSubJob(DootTaskSpec.build({"name": "simple"}))
        tasks = list(obj.make())
        assert(len(tasks) == 3)
        names = [str(x.name) for x in tasks]
        assert("default::simple.$head$" in names)
        assert("default::simple.first" in names)
        assert("default::simple.second" in names)

    def test_setup_teardown(self):
        obj   = SetupTearDownJob(DootTaskSpec.build({"name": "simple"}))
        tasks = list(obj.make())
        assert(len(tasks) == 5)
        names = [str(x.name) for x in tasks]
        assert("default::simple.$head$" in names)
        assert("default::simple.setup" in names)
        assert("default::simple.teardown" in names)
        assert("default::simple.first" in names)
        assert("default::simple.second" in names)
