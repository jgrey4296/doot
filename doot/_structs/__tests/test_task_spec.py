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
from doot.enums import TaskFlags

DEFAULT_CTOR = doot.aliases.task[doot.constants.entrypoints.DEFAULT_TASK_CTOR_ALIAS]

class TestDootTaskSpec:

    def test_raw_ctor(self):
        obj = structs.DootTaskSpec(name="simple::task")
        assert(obj is not None)
        assert(obj.name is not None)

    def test_raw_with_extras(self):
        obj = structs.DootTaskSpec(name="simple::task", blah="bloo")
        assert(obj.blah == "bloo")
        assert("blah" in obj.model_extra)

    def test_extras_are_independent(self):
        obj = structs.DootTaskSpec(name="simple::task", blah="bloo")
        obj2 = structs.DootTaskSpec(name="simple::task", blah="aweg", aweg=2)
        assert(obj.blah == "bloo")
        assert(obj2.blah == "aweg")
        assert("blah" in obj.model_extra)
        assert("blah" in obj2.model_extra)
        assert("aweg" not in obj.model_extra)
        assert("aweg" in obj2.model_extra)

    def test_build(self):
        obj = structs.DootTaskSpec.build({"name":"default::default"})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group == "default")
        assert(obj.name.task == "default")
        assert(str(obj.ctor) == DEFAULT_CTOR)
        assert(obj.version == doot.__version__)

    def test_version(self):
        obj = structs.DootTaskSpec.build({"version" : "0.5", "name":"default::default"})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group == "default")
        assert(obj.name.task == "default")
        assert(str(obj.ctor) == DEFAULT_CTOR)
        assert(obj.version == "0.5")

    def test_basic_name(self):
        obj = structs.DootTaskSpec.build({"name": "agroup::atask"})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group == "agroup")
        assert(obj.name.task == "atask")

    def test_groupless_name(self):
        obj = structs.DootTaskSpec.build({"name": "atask"})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group == "default")
        assert(obj.name.task == "atask")

    def test_with_extra_data(self):
        obj = structs.DootTaskSpec.build({"name": "atask", "blah": "bloo", "something": [1,2,3,4]})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group == "default")
        assert(obj.name.task == "atask")
        assert("blah" in obj.extra)
        assert("something" in obj.extra)

    def test_separate_group_and_task(self):
        obj = structs.DootTaskSpec.build({"name": "atask", "group": "agroup"})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group == "agroup")
        assert(obj.name.task == "atask")


    def test_disabled_spec(self):
        obj = structs.DootTaskSpec.build({"name": "agroup::atask", "disabled":True})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(TaskFlags.DISABLED in obj.flags)

class TestTaskSpecValidation:

    def test_print_level_fail_on_loc(self):
        with pytest.raises(ValueError):
            structs.DootTaskSpec.build({"name":"simple::test", "print_levels":{"blah":"INFO"}})

    def test_print_level_fail_on_level(self):
        with pytest.raises(ValueError):
            structs.DootTaskSpec.build({"name":"simple::test", "print_levels":{"head":"blah"}})

    def test_flag_build(self):
        obj = structs.DootTaskSpec.build({"name":"simple::test"})
        assert(obj.flags == TaskFlags.default)
        assert(obj.flags == TaskFlags.TASK)

    def test_flag_build_multi(self):
        obj = structs.DootTaskSpec.build({"name":"simple::test", "flags": ["TASK", "JOB"]})
        assert(obj.flags == TaskFlags.default | TaskFlags.JOB)

    def test_toml_key_modification(self):
        obj = structs.DootTaskSpec.build({"name":"simple::test", "print-levels": {}})
        assert("print_levels" in obj.model_fields_set)

class TestTaskSpecInstantiation:

    def test_instantiation(self):
        base_task     = structs.DootTaskSpec.build({"name": "base", "group": "agroup", "a": 0})
        override_task = structs.DootTaskSpec.build({"name": "atask", "group": "agroup", "b": 2, "source": "agroup::base"})

        instance = override_task.instantiate_onto(base_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(instance.name != base_task.name)
        assert(override_task.name < instance.name)
        assert("a" in instance.extra)
        assert("b" in instance.extra)
        assert(instance.flags == instance.name.meta)

    def test_instantiation_prefers_newer_extra_vals(self):
        base_task     = structs.DootTaskSpec.build({"name": "base", "group": "agroup", "a": 0})
        override_task = structs.DootTaskSpec.build({"name": "atask", "group": "agroup", "a": 100, "b": 2, "source": "agroup::base"})
        instance = override_task.instantiate_onto(base_task)
        assert(instance.extra['a'] == 100)
        assert(instance.flags == instance.name.meta)

    def test_specialize_from_fail_unrelated(self):
        base_task     = structs.DootTaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = structs.DootTaskSpec.build({"name": "agroup::atask", "b": 2, "source": "agroup::not.base"})

        assert(not base_task.name < structs.DootTaskName.build(override_task.source))
        with pytest.raises(doot.errors.DootTaskTrackingError):
            base_task.specialize_from(override_task)

    def test_specialize_keeps_base_actions(self):
        base_task     = structs.DootTaskSpec.build({"name": "base", "group": "agroup", "a": 0, "actions":[{"do":"basic"}]})
        override_task = structs.DootTaskSpec.build({"name": "atask", "group": "agroup", "b": 2, "source":"agroup::base"})

        instance = base_task.specialize_from(override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(bool(instance.actions))
        assert(instance.flags == instance.name.meta)


    def test_specialize_keeps_override_actions(self):
        base_task     = structs.DootTaskSpec.build({"name": "base", "group": "agroup", "a": 0})
        override_task = structs.DootTaskSpec.build({"name": "atask", "group": "agroup", "b": 2, "actions":[{"do":"basic"}], "source":"agroup::base"})

        instance = base_task.specialize_from(override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(bool(instance.actions))
        assert(instance.flags == instance.name.meta)


    def test_specialize_override_print_levels(self):
        base_task     = structs.DootTaskSpec.build({"name": "base", "group": "agroup", "a": 0, "print_levels": {"head":"DEBUG"}})
        override_task = structs.DootTaskSpec.build({"name": "atask", "group": "agroup", "b": 2, "print_levels": {"head":"WARNING"}, "source":"agroup::base"})

        instance = base_task.specialize_from(override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(instance.print_levels.head == "WARNING")
        assert(instance.flags == instance.name.meta)

    def test_specialize_source_as_taskname(self):
        base_task     = structs.DootTaskSpec.build({"name": "base", "group": "agroup", "a": 0})
        override_task = structs.DootTaskSpec.build({"name": "atask", "group": "agroup", "b": 2, "source" : "agroup::base"})

        instance = base_task.specialize_from(override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(not isinstance(instance.ctor, structs.DootTaskName))
        assert(instance.ctor == base_task.ctor)
        assert(instance.flags == instance.name.meta)

    def test_dependency_merge(self):
        base_task     = structs.DootTaskSpec.build({"name": "base", "group": "agroup", "a": 0, "depends_on": ["basic::dep"]})
        override_task = structs.DootTaskSpec.build({"name": "atask", "group": "agroup", "depends_on": ["extra::dep"], "b": 2, "source" : "agroup::base"})

        instance = base_task.specialize_from(override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(len(instance.depends_on) == 2)
        assert(instance.flags == instance.name.meta)

    def test_specialize_conflict(self):
        base_task     = structs.DootTaskSpec.build({"name": "base", "group": "agroup", "a": 0})
        override_task = structs.DootTaskSpec.build({"name": "atask", "group": "agroup", "b": 1, "source" : "agroup::not.base"})

        with pytest.raises(doot.errors.DootTaskTrackingError):
            base_task.specialize_from(override_task)


    def test_simple_data_extension(self):
        base_task     = structs.DootTaskSpec.build({"name": "base", "group": "agroup", "a": 0, "c": "blah"})
        data = {"a": 2, "b": 3}
        instance = base_task.specialize_from(data)
        assert(instance is not base_task)
        assert(instance.name == base_task.name)
        assert(instance.a == 2)
        assert(instance.b == 3)
        assert(instance.c == "blah")
        assert(instance.flags == instance.name.meta)
