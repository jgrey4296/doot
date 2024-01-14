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
import doot.constants
from doot import structs
from doot.task.base_job import DootJob
from doot.mixins.job.mini_builder import MiniBuilderMixin

class TestDootTaskSpec:

    def test_initial(self):
        obj = structs.DootTaskSpec.from_dict({})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group == "default")
        assert(obj.name.task == "default")
        assert(str(obj.ctor) == doot.constants.DEFAULT_PLUGINS['task'][0][1])
        assert(obj.version == "0.1")

    def test_version_change(self):
        obj = structs.DootTaskSpec.from_dict({"version" : "0.5"})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group == "default")
        assert(obj.name.task == "default")
        assert(str(obj.ctor) == doot.constants.DEFAULT_PLUGINS['task'][0][1])
        assert(obj.version == "0.5")

    def test_basic_name(self):
        obj = structs.DootTaskSpec.from_dict({"name": "agroup::atask"})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group == "agroup")
        assert(obj.name.task == "atask")

    def test_groupless_name(self):
        obj = structs.DootTaskSpec.from_dict({"name": "atask"})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group == "default")
        assert(obj.name.task == "atask")

    def test_with_extra_data(self):
        obj = structs.DootTaskSpec.from_dict({"name": "atask", "blah": "bloo", "something": [1,2,3,4]})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group == "default")
        assert(obj.name.task == "atask")
        assert("blah" in obj.extra)
        assert("something" in obj.extra)

    def test_separate_group_and_task(self):
        obj = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup"})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group == "agroup")
        assert(obj.name.task == "atask")

class TestSpecMixinBuild:

    def test_basic(self):
        spec = structs.DootTaskSpec.from_dict({"name": "basic",
                                       "ctor": "doot.task.base_job:DootJob",
                                       "mixins": ["doot.mixins.job.mini_builder:MiniBuilderMixin"],

                                      })
        task = spec.build()
        assert(isinstance(task,DootJob))
        assert(MiniBuilderMixin in task.__class__.mro())
        assert(isinstance(task, MiniBuilderMixin))


class TestTaskSpecSpecialization:

    def test_specialize_from(self):
        base_task     = structs.DootTaskSpec.from_dict({"name": "base", "group": "agroup", "extra": {"a": 0}})
        override_task = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup", "extra": {"b": 2},
                                                        "ctor": structs.DootTaskName.from_str("agroup::base")})

        specialized = base_task.specialize_from(override_task)
        assert(specialized is not base_task)
        assert(specialized is not override_task)
        assert("a" in specialized.extra)
        assert("b" in specialized.extra)

    def test_specialize_actions_from(self):
        base_task     = structs.DootTaskSpec.from_dict({"name": "base", "group": "agroup", "extra": {"a": 0}, "actions":[{"do":"blah"}]})
        override_task = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup", "extra": {"b": 2},
                                                        "ctor": structs.DootTaskName.from_str("agroup::base")})

        specialized = base_task.specialize_from(override_task)
        assert(specialized is not base_task)
        assert(specialized is not override_task)
        assert(bool(specialized.actions))

    def test_specialize_actions_from_inverse(self):
        base_task     = structs.DootTaskSpec.from_dict({"name": "base", "group": "agroup", "extra": {"a": 0}})
        override_task = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup", "extra": {"b": 2}, "actions":[{"do":"blah"}],
                                                        "ctor": structs.DootTaskName.from_str("agroup::base")})

        specialized = base_task.specialize_from(override_task)
        assert(specialized is not base_task)
        assert(specialized is not override_task)
        assert(bool(specialized.actions))

    def test_specialize_print_levels(self):
        base_task     = structs.DootTaskSpec.from_dict({"name": "base", "group": "agroup", "extra": {"a": 0}, "print_levels": {"head":"DEBUG"}})
        override_task = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup", "extra": {"b": 2}, "print_levels": {"head":"WARNING"},
                                                        "ctor": structs.DootTaskName.from_str("agroup::base")})

        specialized = base_task.specialize_from(override_task)
        assert(specialized is not base_task)
        assert(specialized is not override_task)
        assert(specialized.print_levels.head == "WARNING")


    def test_specialize_ctor_as_taskname(self):
        base_task     = structs.DootTaskSpec.from_dict({"name": "base", "group": "agroup", "extra": {"a": 0}})
        override_task = structs.DootTaskSpec.from_dict({"name": "atask",
                                                        "group": "agroup",
                                                        "extra": {"b": 2},
                                                        "ctor" : structs.DootTaskName.from_str("agroup::base")
                                                       })

        specialized = base_task.specialize_from(override_task)
        assert(specialized is not base_task)
        assert(specialized is not override_task)
        assert(not isinstance(specialized.ctor, structs.DootTaskName))
        assert(specialized.ctor == base_task.ctor)


    def test_dependency_merge(self):
        base_task     = structs.DootTaskSpec.from_dict({"name": "base", "group": "agroup", "extra": {"a": 0}, "depends_on": ["basic::dep"]})
        override_task = structs.DootTaskSpec.from_dict({"name": "atask",
                                                        "group": "agroup",
                                                        "depends_on": ["extra::dep"],
                                                        "extra": {"b": 2},
                                                        "ctor" : structs.DootTaskName.from_str("agroup::base")
                                                       })

        specialized = base_task.specialize_from(override_task)
        assert(specialized is not base_task)
        assert(specialized is not override_task)
        assert(len(specialized.depends_on) == 2)


    def test_specialize_conflict(self):
        base_task     = structs.DootTaskSpec.from_dict({"name": "base", "group": "agroup", "extra": {"a": 0}})
        override_task = structs.DootTaskSpec.from_dict({"name": "atask",
                                                        "group": "agroup",
                                                        "extra": {"b": 2},
                                                        "ctor" : structs.DootTaskName.from_str("agroup::not.base")
                                                       })

        with pytest.raises(doot.errors.DootTaskTrackingError):
            base_task.specialize_from(override_task)
