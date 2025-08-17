#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN202, N812, PLR2004
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings

import pytest

from jgdv.structs.strang import CodeReference
from jgdv.structs.chainguard import ChainGuard
import doot
import doot.errors

from ... import DootJob
from ... import _interface as API
from ..._interface import TaskMeta_e, Task_p
from .. import TaskSpec, TaskName
from doot.util.factory import TaskFactory

logging       = logmod.root

factory       = TaskFactory()
DEFAULT_CTOR  = CodeReference(doot.aliases.task[doot.constants.entrypoints.DEFAULT_TASK_CTOR_ALIAS])

class TestTaskSpec:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_ctor(self):
        assert(isinstance(TaskSpec, API.SpecStruct_p))

    def test_raw_ctor(self):
        obj = TaskSpec(name="simple::task")
        assert(obj is not None)
        assert(obj.name is not None)
        assert(isinstance(obj, TaskSpec))
        assert(isinstance(obj, API.TaskSpec_i))

    def test_raw_with_extras(self):
        obj = TaskSpec(name="simple::task", blah="bloo")
        assert(obj.blah == "bloo")
        assert("blah" in obj.model_extra)

    def test_extras_are_independent(self):
        obj = TaskSpec(name="simple::task", blah="bloo")
        obj2 = TaskSpec(name="simple::task", blah="aweg", aweg=2)
        assert(obj.blah == "bloo")
        assert(obj2.blah == "aweg")
        assert("blah" in obj.model_extra)
        assert("blah" in obj2.model_extra)
        assert("aweg" not in obj.model_extra)
        assert("aweg" in obj2.model_extra)

    def test_build(self):
        obj = factory.build({"name":"default::default"})
        assert(isinstance(obj, TaskSpec))
        assert(obj.name[0,:]== "default")
        assert(obj.name[1,:] == "default")
        assert(obj.ctor is None)
        assert(obj.version == doot.__version__)

    def test_version(self):
        obj = factory.build({"version" : "0.5", "name":"default::default"})
        assert(isinstance(obj, TaskSpec))
        assert(obj.name[0,:] == "default")
        assert(obj.name[1,:] == "default")
        assert(obj.ctor is None)
        assert(obj.version == "0.5")

    def test_basic_name(self):
        obj = factory.build({"name": "agroup::atask"})
        assert(isinstance(obj, TaskSpec))
        assert(obj.name[0,:] == "agroup")
        assert(obj.name[1,:] == "atask")

    def test_groupless_name(self):
        with pytest.raises(ValueError):
            factory.build({"name": "atask"})

    def test_with_extra_data(self):
        obj = factory.build({"name": "agroup::atask", "blah": "bloo", "something": [1,2,3,4]})
        assert(isinstance(obj, TaskSpec))
        assert(obj.name == "agroup::atask")
        assert("blah" in obj.extra)
        assert("something" in obj.extra)

    def test_separate_group_and_task(self):
        obj = factory.build({"name": "atask", "group": "agroup"})
        assert(isinstance(obj, TaskSpec))
        assert(obj.name[0,:] == "agroup")
        assert(obj.name[1,:] == "atask")

    def test_disabled_spec(self):
        obj = factory.build({"name": "agroup::atask", "disabled":True})
        assert(isinstance(obj, TaskSpec))
        assert(TaskMeta_e.DISABLED in obj.meta)

    def test_sources_empty(self):
        obj = factory.build({"name": "agroup::atask"})
        assert(isinstance(obj.sources, list))
        assert(not bool(obj.sources))

    def test_sources_name(self):
        obj = factory.build({"name": "agroup::atask", "sources":["other::task"]})
        assert(isinstance(obj.sources, list))
        assert(bool(obj.sources))
        assert(obj.sources[0] == "other::task")

    def test_sources_path(self):
        obj = factory.build({"name": "agroup::atask", "sources":["a/path.txt"]})
        assert(isinstance(obj.sources, list))
        assert(bool(obj.sources))
        assert(obj.sources[0] == pl.Path("a/path.txt"))

    def test_sources_multi(self):
        obj = factory.build({"name": "agroup::atask", "sources":["a/path.txt", "other::task"]})
        assert(isinstance(obj.sources, list))
        assert(bool(obj.sources))
        assert(obj.sources[0] == pl.Path("a/path.txt"))
        assert(obj.sources[1] == "other::task")

    def test_requires_head(self):
        obj = factory.build({"name":"agroup::atask", "required_for":["agroup::ajob..$head$"]})
        assert(len(obj.required_for) == 2)

class TestTaskSpec_Validation:
    """ Tests the validation methods of the spec

    """

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_meta_build(self):
        obj = factory.build({"name":"simple::test"})
        assert(obj.meta == {TaskMeta_e.default()})
        assert(obj.meta  == {TaskMeta_e.TASK})

    def test_meta_build_multi(self):
        obj = factory.build({"name":"simple::+.test"}) #, "meta": ["TASK", "JOB"]})
        assert(obj.meta == {TaskMeta_e.JOB})

    def test_toml_key_modification(self):
        obj = factory.build({"name":"simple::test", "blah": {}})
        assert("blah" in obj.model_fields_set)

    def test_sources_fail_if_partial(self):
        with pytest.raises(ValueError):
            factory.build({"name":"simple::test", "sources": ["basic::some.other..$partial$"]})

    def test_action_group_sorting(self):
        spec = factory.build({"name":"simple::test",
                               "actions": [
                                   {"do":"log:log"},
                                   {"do":"blah:bloo"},
                                   {"do":"aweg:aweg"},
                               ]})
        for x,y in zip(spec.actions, ["log:log", "blah:bloo", "aweg:aweg"], strict=True):
            assert(x.do[:] == y)

    def test_implicit_job_relations(self):
        spec = factory.build({"name":"simple::test",
                               "depends_on" : ["simple::+.job..$head$"],
                               })
        assert(len(spec.depends_on) == 2)
        assert(spec.depends_on[0].target == "simple::+.job")
        assert(spec.depends_on[1].target == "simple::+.job..$head$")

    def test_implicit_cleanup_relations(self):
        spec = factory.build({"name":"simple::test",
                               "depends_on" : ["simple::task..$cleanup$"],
                               })
        assert(len(spec.depends_on) == 2)
        assert(spec.depends_on[0].target == "simple::task")
        assert(spec.depends_on[1].target == "simple::task..$cleanup$")
