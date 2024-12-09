#!/usr/bin/env python3
"""

"""
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import unittest
import warnings
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
doot._test_setup()
import doot.errors
import doot.structs
from doot._abstract import Task_i
from doot.control.comptracker.track_registry import TrackRegistry
from doot.enums import TaskStatus_e
from doot.utils import mock_gen

# ##-- end 1st party imports

logging = logmod.root

class TestRegistry:

    def test_sanity(self):
        obj = TrackRegistry()
        assert(obj is not None)

    def test_register_spec(self):
        obj = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        assert(not bool(obj.specs))
        obj.register_spec(spec)
        assert(bool(obj.specs))
        assert(len(obj.specs) == 2)

    def test_register_job_spec(self):
        obj = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "ctor":"doot.task.base_job:DootJob"})
        assert(not bool(obj.specs))
        obj.register_spec(spec)
        assert(bool(obj.specs))
        assert(spec.name in obj.specs)
        assert(spec.name.with_head() in obj.specs)
        assert(not bool(obj.concrete[spec.name]))

    def test_register_is_idempotent(self):
        obj  = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        assert(not bool(obj.specs))
        assert(not bool(obj.concrete[spec.name]))
        assert(len(obj.specs) == 0)
        for _ in range(5):
            obj.register_spec(spec)
            assert(len(obj.specs) == 2) # the spec, and cleanup
            assert(len(obj.concrete[spec.name]) == 0)

    def test_register_spec_with_artifacts(self):
        obj  = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["file::test.txt"], "required_for": ["file::other.txt"]})
        assert(not bool(obj.artifacts))
        obj.register_spec(spec)
        assert(bool(obj.artifacts))
        assert(len(obj.artifacts) == 2)

    def test_register_spec_with_subtasks(self):
        obj  = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["basic::sub.1", "basic::sub.2"], "required_for": ["basic::super.1"]})
        assert(not bool(obj.specs))
        obj.register_spec(spec)
        assert(bool(obj.specs))
        assert(len(obj.specs) == 2)

    def test_register_spec_ignores_disabled(self):
        obj = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "disabled":True})
        assert(len(obj.specs) == 0)
        obj.register_spec(spec)
        assert(len(obj.specs) == 0)

    @pytest.mark.xfail
    def test_register_transformer_spec(self):
        obj = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::transformer", "meta":"TRANSFORMER", "depends_on": ["file::?.txt"], "required_for": ["file::?.blah"]})
        assert(len(obj.specs) == 0)
        assert(len(obj._transformer_specs) == 0)
        obj.register_spec(spec)
        assert(len(obj.specs) == 2)
        assert(len(obj._transformer_specs) == 2)
        assert("?.txt" in obj._transformer_specs)
        assert("?.blah" in obj._transformer_specs)

    def test_spec_retrieval(self):
        obj = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        retrieved = obj.specs[name]
        assert(retrieved == spec)

    def test_make_task(self):
        obj = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        assert(not bool(obj.tasks))
        obj._make_task(instance)
        assert(bool(obj.tasks))

    def test_task_retrieval(self):
        obj = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        result = obj._make_task(instance)
        retrieved = obj.tasks[result]
        assert(isinstance(retrieved, Task_i))

    def test_task_get_default_status(self):
        obj = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        result   = obj._make_task(instance)
        status   = obj.get_status(result)
        assert(status is TaskStatus_e.INIT)

    def test_task_status_missing_task(self):
        obj = TrackRegistry()
        name = doot.structs.TaskName("basic::task")
        assert(obj.get_status(name) == TaskStatus_e.NAMED)

    def test_set_status(self):
        obj = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        result = obj._make_task(instance)
        assert(obj.get_status(result) is TaskStatus_e.INIT)
        assert(obj.set_status(result, TaskStatus_e.SUCCESS) is True)
        assert(obj.get_status(result) is TaskStatus_e.SUCCESS)

    def test_set_status_missing_task(self):
        obj = TrackRegistry()
        name = doot.structs.TaskName("basic::task")
        assert(obj.set_status(name, TaskStatus_e.SUCCESS) is False)


class TestRegistryInternals:

    def test_basic(self):
        obj = TrackRegistry()
        assert(obj is not None)

    def test_instantiate_spec_no_op(self):
        obj       = TrackRegistry()
        base_spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        spec      = doot.structs.TaskSpec.build({"name":"test::spec"})
        obj.register_spec(base_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec is not special)
        assert(spec is not base_spec)
        assert(spec.name < special)
        assert(special in obj.concrete[spec.name])

    def test_instantiate_spec(self):
        obj = TrackRegistry()
        base_spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        dep_spec = doot.structs.TaskSpec.build({"name": "example::dep"})
        spec    = doot.structs.TaskSpec.build({"name":"test::spec", "sources": "basic::task", "bloo": 15})
        obj.register_spec(base_spec, dep_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.TaskName))
        assert(special in obj.concrete[spec.name])

    def test_instantiate_spec_match_reuse(self):
        obj = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        obj.register_spec(spec)
        instances = set()
        for i in range(5):
            instance = obj._instantiate_spec(spec.name)
            assert(isinstance(instance, doot.structs.TaskName))
            assert(instance in obj.concrete[spec.name])
            instances.add(instance)
            assert(spec.name < instance)
            assert(obj.specs[instance] is not obj.specs[spec.name])
            assert(len(obj.concrete[spec.name]) == 1)
        assert(len(instances) == 1)

    def test_instantiate_job_head(self):
        obj = TrackRegistry()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "ctor": "doot.task.base_job:DootJob", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        abs_head = spec.name.with_head()
        obj.register_spec(spec)
        instance = obj._instantiate_spec(spec.name)
        inst_head = instance.with_head()
        assert(instance in obj.specs)
        assert(abs_head in obj.specs)
        assert(instance in obj.concrete[spec.name])
        assert(spec.name < abs_head)
        assert(spec.name < instance)
        assert(instance < inst_head)

    def test_instantiate_spec_chain(self):
        obj = TrackRegistry()
        base_spec = doot.structs.TaskSpec.build({"name":"basic::task", "blah": 2, "bloo": 5})
        dep_spec = doot.structs.TaskSpec.build({"name": "example::dep", "sources":"basic::task", "bloo":10, "aweg":15 })
        spec    = doot.structs.TaskSpec.build({"name":"test::spec", "sources": "example::dep", "aweg": 20})
        obj.register_spec(base_spec, dep_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.TaskName))

    @pytest.mark.xfail
    def test_instantiate_spec_name_change(self):
        obj       = TrackRegistry()
        base_spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        dep_spec = doot.structs.TaskSpec.build({"name": "example::dep"})
        spec    = doot.structs.TaskSpec.build({"name":"test::spec", "sources": "basic::task", "bloo": 15})
        obj.register_spec(base_spec, dep_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.TaskName))
        assert(spec.name < special)
        assert(isinstance(special.tail[-1], UUID))

    def test_instantiate_spec_extra_merge(self):
        obj = TrackRegistry()
        base_spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        dep_spec = doot.structs.TaskSpec.build({"name": "example::dep"})
        spec    = doot.structs.TaskSpec.build({"name":"test::spec", "sources": "basic::task", "bloo": 15, "aweg": "aweg"})
        obj.register_spec(base_spec, dep_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.TaskName))
        concrete = obj.specs[special]
        assert(concrete.extra.blah == 2)
        assert(concrete.extra.bloo == 15)

    def test_instantiate_spec_depends_merge(self):
        obj = TrackRegistry()
        base_spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"]})
        dep_spec = doot.structs.TaskSpec.build({"name": "example::dep"})
        dep_spec2 = doot.structs.TaskSpec.build({"name": "another::dep"})
        spec    = doot.structs.TaskSpec.build({"name":"test::spec", "sources": "basic::task", "depends_on":["another::dep"]})
        obj.register_spec(base_spec, dep_spec, dep_spec2, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.TaskName))
        concrete = obj.specs[special]
        assert(len(concrete.depends_on) == 2)
        assert(any("example::dep" in x.target for x in concrete.depends_on))
        assert(any("another::dep" in x.target for x in concrete.depends_on))
