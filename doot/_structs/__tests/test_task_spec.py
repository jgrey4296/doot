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
from doot import structs
import doot.constants

# caplog
# mocker.patch | patch.object | patch.multiple | patch.dict | stopall | stop | spy | stub
# pytest.mark.filterwarnings
# pytest.parameterize
# pytest.skip | skipif | xfail
# with pytest.deprecated_call
# with pytest.raises
# with pytest.warns(warntype)

class TestDootTaskSpec:

    def test_initial(self):
        obj = structs.DootTaskSpec.from_dict({})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group_str() == "default")
        assert(obj.name.task_str() == "default")
        assert(str(obj.ctor_name) == doot.constants.DEFAULT_PLUGINS['tasker'][0][1])
        assert(obj.version == "0.1")


    def test_version_change(self):
        obj = structs.DootTaskSpec.from_dict({"version" : "0.5"})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group_str() == "default")
        assert(obj.name.task_str() == "default")
        assert(str(obj.ctor_name) == doot.constants.DEFAULT_PLUGINS['tasker'][0][1])
        assert(obj.version == "0.5")


    def test_basic_name(self):
        obj = structs.DootTaskSpec.from_dict({"name": "agroup::atask"})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group_str() == "agroup")
        assert(obj.name.task_str() == "atask")


    def test_groupless_name(self):
        obj = structs.DootTaskSpec.from_dict({"name": "atask"})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group_str() == "default")
        assert(obj.name.task_str() == "atask")


    def test_with_extra_data(self):
        obj = structs.DootTaskSpec.from_dict({"name": "atask", "blah": "bloo", "something": [1,2,3,4]})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group_str() == "default")
        assert(obj.name.task_str() == "atask")
        assert("blah" in obj.extra)
        assert("something" in obj.extra)


    def test_separate_group_and_task(self):
        obj = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup"})
        assert(isinstance(obj, structs.DootTaskSpec))
        assert(obj.name.group_str() == "agroup")
        assert(obj.name.task_str() == "atask")


    def test_specialize_from(self):
        base_task     = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup", "extra": {"a": 0}})
        override_task = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup", "extra": {"b": 2}})

        specialized = base_task.specialize_from(override_task)
        assert(specialized is not base_task)
        assert(specialized is not override_task)
        assert("a" in specialized.extra)
        assert("b" in specialized.extra)


    def test_specialize_actions_from(self):
        base_task     = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup", "extra": {"a": 0}, "actions":[{"do":"blah"}]})
        override_task = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup", "extra": {"b": 2}})

        specialized = base_task.specialize_from(override_task)
        assert(specialized is not base_task)
        assert(specialized is not override_task)
        assert(bool(specialized.actions))


    def test_specialize_actions_from_inverse(self):
        base_task     = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup", "extra": {"a": 0}})
        override_task = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup", "extra": {"b": 2}, "actions":[{"do":"blah"}]})

        specialized = base_task.specialize_from(override_task)
        assert(specialized is not base_task)
        assert(specialized is not override_task)
        assert(bool(specialized.actions))


    def test_specialize_print_levels(self):
        base_task     = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup", "extra": {"a": 0}, "print_levels": {"head":"DEBUG"}})
        override_task = structs.DootTaskSpec.from_dict({"name": "atask", "group": "agroup", "extra": {"b": 2}, "print_levels": {"head":"WARNING"}})

        specialized = base_task.specialize_from(override_task)
        assert(specialized is not base_task)
        assert(specialized is not override_task)
        assert(specialized.print_levels.head == "WARNING")
