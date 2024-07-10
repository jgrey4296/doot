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

import tomlguard
import doot
import doot.errors

doot._test_setup()
from doot import structs
from doot.task.base_job import DootJob
from doot.enums import TaskMeta_f

DEFAULT_CTOR = doot.aliases.task[doot.constants.entrypoints.DEFAULT_TASK_CTOR_ALIAS]

class TestTaskSpec:

    def test_raw_ctor(self):
        obj = structs.TaskSpec(name="simple::task")
        assert(obj is not None)
        assert(obj.name is not None)

    def test_raw_with_extras(self):
        obj = structs.TaskSpec(name="simple::task", blah="bloo")
        assert(obj.blah == "bloo")
        assert("blah" in obj.model_extra)

    def test_extras_are_independent(self):
        obj = structs.TaskSpec(name="simple::task", blah="bloo")
        obj2 = structs.TaskSpec(name="simple::task", blah="aweg", aweg=2)
        assert(obj.blah == "bloo")
        assert(obj2.blah == "aweg")
        assert("blah" in obj.model_extra)
        assert("blah" in obj2.model_extra)
        assert("aweg" not in obj.model_extra)
        assert("aweg" in obj2.model_extra)

    def test_build(self):
        obj = structs.TaskSpec.build({"name":"default::default"})
        assert(isinstance(obj, structs.TaskSpec))
        assert(obj.name.group == "default")
        assert(obj.name.task == "default")
        assert(str(obj.ctor) == DEFAULT_CTOR)
        assert(obj.version == doot.__version__)

    def test_version(self):
        obj = structs.TaskSpec.build({"version" : "0.5", "name":"default::default"})
        assert(isinstance(obj, structs.TaskSpec))
        assert(obj.name.group == "default")
        assert(obj.name.task == "default")
        assert(str(obj.ctor) == DEFAULT_CTOR)
        assert(obj.version == "0.5")

    def test_basic_name(self):
        obj = structs.TaskSpec.build({"name": "agroup::atask"})
        assert(isinstance(obj, structs.TaskSpec))
        assert(obj.name.group == "agroup")
        assert(obj.name.task == "atask")

    def test_groupless_name(self):
        with pytest.raises(ValueError):
            structs.TaskSpec.build({"name": "atask"})

    def test_with_extra_data(self):
        obj = structs.TaskSpec.build({"name": "agroup::atask", "blah": "bloo", "something": [1,2,3,4]})
        assert(isinstance(obj, structs.TaskSpec))
        assert(obj.name == "agroup::atask")
        assert("blah" in obj.extra)
        assert("something" in obj.extra)

    def test_separate_group_and_task(self):
        obj = structs.TaskSpec.build({"name": "atask", "group": "agroup"})
        assert(isinstance(obj, structs.TaskSpec))
        assert(obj.name.group == "agroup")
        assert(obj.name.task == "atask")

    def test_disabled_spec(self):
        obj = structs.TaskSpec.build({"name": "agroup::atask", "disabled":True})
        assert(isinstance(obj, structs.TaskSpec))
        assert(TaskMeta_f.DISABLED in obj.flags)

    def test_sources_empty(self):
        obj = structs.TaskSpec.build({"name": "agroup::atask"})
        assert(isinstance(obj.sources, list))
        assert(not bool(obj.sources))

    def test_sources_name(self):
        obj = structs.TaskSpec.build({"name": "agroup::atask", "sources":["other::task"]})
        assert(isinstance(obj.sources, list))
        assert(bool(obj.sources))
        assert(obj.sources[0] == "other::task")

    def test_sources_path(self):
        obj = structs.TaskSpec.build({"name": "agroup::atask", "sources":["a/path.txt"]})
        assert(isinstance(obj.sources, list))
        assert(bool(obj.sources))
        assert(obj.sources[0] == pl.Path("a/path.txt"))

    def test_sources_multi(self):
        obj = structs.TaskSpec.build({"name": "agroup::atask", "sources":["a/path.txt", "other::task"]})
        assert(isinstance(obj.sources, list))
        assert(bool(obj.sources))
        assert(obj.sources[0] == pl.Path("a/path.txt"))
        assert(obj.sources[1] == "other::task")

class TestTaskSpecValidation:

    def test_flag_build(self):
        obj = structs.TaskSpec.build({"name":"simple::test"})
        assert(obj.flags == TaskMeta_f.default)
        assert(obj.flags == TaskMeta_f.TASK)

    def test_flag_build_multi(self):
        obj = structs.TaskSpec.build({"name":"simple::test", "flags": ["TASK", "JOB"]})
        assert(obj.flags == TaskMeta_f.default | TaskMeta_f.JOB)

    def test_toml_key_modification(self):
        obj = structs.TaskSpec.build({"name":"simple::test", "blah": {}})
        assert("blah" in obj.model_fields_set)

    def test_match_with_constraints_pass(self):
        spec1 = structs.TaskSpec.build({"name":"simple::test"})
        spec2 = structs.TaskSpec.build({"name":"simple::test"})
        assert(spec1.match_with_constraints(spec2))

    def test_match_with_constraints_instanced(self):
        spec1 = structs.TaskSpec.build({"name":"simple::test"}).instantiate_onto(None)
        spec2 = structs.TaskSpec.build({"name":"simple::test"})
        assert(spec1.match_with_constraints(spec2))

    def test_match_with_constraints_with_value(self):
        spec1 = structs.TaskSpec.build({"name":"simple::test", "blah":5}).instantiate_onto(None)
        spec2 = structs.TaskSpec.build({"name":"simple::test", "blah":5})
        assert(spec1.match_with_constraints(spec2))

    def test_match_with_constraints_with_value_fail(self):
        spec1 = structs.TaskSpec.build({"name":"simple::test", "blah":10}).instantiate_onto(None)
        spec2 = structs.TaskSpec.build({"name":"simple::test", "blah":5})
        assert(not spec1.match_with_constraints(spec2))

    def test_match_with_contraints_missing_value_from_control(self):
        spec1 = structs.TaskSpec.build({"name":"simple::test", "blah":5}).instantiate_onto(None)
        spec2 = structs.TaskSpec.build({"name":"simple::test", "blah":5, "bloo": 10})
        assert(not spec1.match_with_constraints(spec2))

class TestTaskSpecInstantiation:

    def test_instantiation(self):
        base_task     = structs.TaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = structs.TaskSpec.build({"name": "agroup::atask", "b": 2, "sources": "agroup::base"})

        instance = override_task.instantiate_onto(base_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(instance.name != base_task.name)
        assert(override_task.name < instance.name)
        assert("a" in instance.extra)
        assert("b" in instance.extra)
        assert(instance.flags == instance.name.meta)
        assert(instance.sources == ["agroup::base", "agroup::atask"])

    def test_instantiation_extends_sources(self):
        base_task     = structs.TaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = structs.TaskSpec.build({"name": "agroup::atask", "b": 2, "sources": "agroup::base"})
        instance = override_task.instantiate_onto(base_task)
        assert(instance.sources == ["agroup::base", "agroup::atask"])

    def test_instantiation_prefers_newer_extra_vals(self):
        base_task     = structs.TaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = structs.TaskSpec.build({"name": "agroup::atask", "a": 100, "b": 2, "sources": "agroup::base"})
        instance = override_task.instantiate_onto(base_task)
        assert(instance.extra['a'] == 100)
        assert(instance.flags == instance.name.meta)
        assert(instance.sources == ["agroup::base", "agroup::atask"])

    def test_specialize_from_fail_unrelated(self):
        base_task     = structs.TaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = structs.TaskSpec.build({"name": "agroup::atask", "b": 2, "sources": "agroup::not.base"})

        assert(not base_task.name < structs.TaskName.build(override_task.sources[-1]))
        with pytest.raises(doot.errors.DootTaskTrackingError):
            base_task.specialize_from(override_task)

    def test_specialize_keeps_base_actions(self):
        base_task     = structs.TaskSpec.build({"name": "agroup::base", "a": 0, "actions":[{"do":"basic"}]})
        override_task = structs.TaskSpec.build({"name": "agroup::atask", "b": 2, "sources":"agroup::base"})

        instance = base_task.specialize_from(override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(bool(instance.actions))
        assert(instance.flags == instance.name.meta)

    def test_specialize_keeps_override_actions(self):
        base_task     = structs.TaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = structs.TaskSpec.build({"name": "agroup::atask", "b": 2, "actions":[{"do":"basic"}], "sources":"agroup::base"})

        instance = base_task.specialize_from(override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(bool(instance.actions))
        assert(instance.flags == instance.name.meta)

    def test_specialize_source_as_taskname(self):
        base_task     = structs.TaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = structs.TaskSpec.build({"name": "agroup::atask", "b": 2, "sources" : "agroup::base"})

        instance = base_task.specialize_from(override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(not isinstance(instance.ctor, structs.TaskName))
        assert(instance.ctor == base_task.ctor)
        assert(instance.flags == instance.name.meta)

    def test_dependency_merge(self):
        base_task     = structs.TaskSpec.build({"name": "agroup::base", "a": 0, "depends_on": ["basic::dep"]})
        override_task = structs.TaskSpec.build({"name": "agroup::atask", "depends_on": ["extra::dep"], "b": 2, "sources" : "agroup::base"})

        instance = base_task.specialize_from(override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(len(instance.depends_on) == 2)
        assert(instance.flags == instance.name.meta)

    def test_specialize_conflict(self):
        base_task     = structs.TaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = structs.TaskSpec.build({"name": "agroup::atask", "b": 1, "sources" : "agroup::not.base"})

        with pytest.raises(doot.errors.DootTaskTrackingError):
            base_task.specialize_from(override_task)

    def test_simple_data_extension(self):
        base_task     = structs.TaskSpec.build({"name": "agroup::base", "a": 0, "c": "blah"})
        data = {"a": 2, "b": 3}
        instance = base_task.specialize_from(data)
        assert(instance is not base_task)
        assert(instance.name == base_task.name)
        assert(instance.a == 2)
        assert(instance.b == 3)
        assert(instance.c == "blah")
        assert(instance.flags == instance.name.meta)

    def test_sources_independece(self):
        base_task     = structs.TaskSpec.build({"name": "agroup::base", "a": 0, "c": "blah"})
        second = structs.TaskSpec.build(dict(base_task))
        assert(base_task.sources is not second.sources)
        second.sources.append("blah")
        assert("blah" not in base_task.sources)

    def test_dict_sources_independence(self):
        base_task     = structs.TaskSpec.build({"name": "agroup::base", "a": 0, "c": "blah"})
        instance = base_task.specialize_from({})
        assert(base_task.sources is not instance.sources)
        instance.sources.append("blah")
        assert("blah" not in base_task.sources)

    def test_self_sources_independence(self):
        base_task     = structs.TaskSpec.build({"name": "agroup::base", "a": 0, "c": "blah"})
        instance = base_task.specialize_from(base_task)
        assert(base_task.sources is not instance.sources)
        instance.sources.append("blah")
        assert("blah" not in base_task.sources)
