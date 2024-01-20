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
from doot.structs import DootTaskSpec, TaskStub, DootCodeReference
from doot.task.base_job import DootJob
from doot.mixins.job.subtask import SubMixin
import doot._abstract

sub_ref   = DootCodeReference.from_str("doot.task.base_job:DootJob").add_mixins("doot.mixins.job.subtask:SubMixin")
SubJob = sub_ref.try_import()

class SimpleSubJob(SubJob):

    def _build_subs(self):
        yield DootTaskSpec(name=self.fullname.subtask("first"))
        yield DootTaskSpec(name=self.fullname.subtask("second"))

    def alt_subgen(self):
        yield DootTaskSpec(name=self.fullname.subtask("alt_first"))
        yield DootTaskSpec(name=self.fullname.subtask("alt_second"))

class SetupTearDownJob(SimpleSubJob):

    def build(self, **kwargs):
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
        obj = SimpleSubJob(DootTaskSpec.from_dict({"name": "simple"}))
        assert(isinstance(obj, doot._abstract.TaskBase_i))


    def test_custom_subgen(self):
        obj = SimpleSubJob(DootTaskSpec.from_dict({"name": "simple", "sub_generator": SimpleSubJob.alt_subgen }))
        assert(isinstance(obj, doot._abstract.TaskBase_i))
        tasks = list(obj.build())
        assert(len(tasks) == 3)
        names = [str(x.name) for x in tasks]
        assert("default::simple.$head$" in names)
        assert("default::simple.alt_first" in names)
        assert("default::simple.alt_second" in names)

    def test_builds_task(self):
        obj   = SimpleSubJob(DootTaskSpec.from_dict({"name": "simple"}))
        tasks = list(obj.build())
        assert(len(tasks) == 3)
        names = [str(x.name) for x in tasks]
        assert("default::simple.$head$" in names)
        assert("default::simple.first" in names)
        assert("default::simple.second" in names)

    def test_setup_teardown(self):
        obj   = SetupTearDownJob(DootTaskSpec.from_dict({"name": "simple"}))
        tasks = list(obj.build())
        assert(len(tasks) == 5)
        names = [str(x.name) for x in tasks]
        assert("default::simple.$head$" in names)
        assert("default::simple.setup" in names)
        assert("default::simple.teardown" in names)
        assert("default::simple.first" in names)
        assert("default::simple.second" in names)
