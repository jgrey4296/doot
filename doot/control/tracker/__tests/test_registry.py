#!/usr/bin/env python3
"""

"""
# Imports:
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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.util import mock_gen
from doot.workflow._interface import TaskStatus_e
from doot.workflow import TaskName, TaskSpec, InjectSpec

# ##-- end 1st party imports

# ##-| Local
from ..registry import TrackRegistry

# # End of Imports.

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|
from doot.workflow._interface import Task_p
# isort: on
# ##-- end types
logging = logmod.root

class TestRegistry:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_task_retrieval(self):
        obj  = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance  = obj._instantiate_spec(name)
        result    = obj._make_task(instance)
        retrieved = obj.tasks[result]
        assert(isinstance(retrieved, Task_p))

    def test_task_get_default_status(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        result   = obj._make_task(instance)
        status   = obj.get_status(result)
        assert(status is TaskStatus_e.INIT)

    def test_task_status_missing_task(self):
        obj = TrackRegistry()
        name = TaskName("basic::task")
        assert(obj.get_status(name) == TaskStatus_e.NAMED)

    def test_set_status(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        result = obj._make_task(instance)
        assert(obj.get_status(result) is TaskStatus_e.INIT)
        assert(obj.set_status(result, TaskStatus_e.SUCCESS) is True)
        assert(obj.get_status(result) is TaskStatus_e.SUCCESS)

    def test_set_status_missing_task(self):
        obj = TrackRegistry()
        name = TaskName("basic::task")
        assert(obj.set_status(name, TaskStatus_e.SUCCESS) is False)

    def test_spec_retrieval(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        retrieved = obj.specs[name]
        assert(retrieved == spec)

class TestRegistration:

    def test_sanity(self):
        obj = TrackRegistry()
        assert(obj is not None)

    def test_register_spec(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        assert(not bool(obj.specs))
        obj.register_spec(spec)
        assert(bool(obj.specs))
        assert(len(obj.specs) == 2)

    def test_register_spec_cleanup(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        assert(not bool(obj.specs))
        obj.register_spec(spec)
        assert(spec.name.with_cleanup() in obj.specs)

    def test_register_job_spec(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task", "ctor":"doot.workflow:DootJob"})
        assert(not bool(obj.specs))
        obj.register_spec(spec)
        assert(bool(obj.specs))
        assert(spec.name in obj.specs)
        assert(spec.name.with_head() in obj.specs)
        assert(not bool(obj.concrete[spec.name]))

    def test_register_is_idempotent(self):
        obj  = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        assert(not bool(obj.specs))
        assert(not bool(obj.concrete[spec.name]))
        assert(len(obj.specs) == 0)
        for _ in range(5):
            obj.register_spec(spec)
            assert(len(obj.specs) == 2) # the spec, and cleanup
            assert(len(obj.concrete[spec.name]) == 0)

    def test_register_spec_with_artifacts(self):
        obj  = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task", "depends_on":["file::>test.txt"], "required_for": ["file::>other.txt"]})
        assert(not bool(obj.artifacts))
        obj.register_spec(spec)
        assert(bool(obj.artifacts))
        assert(len(obj.artifacts) == 2)

    def test_register_spec_with_subtasks(self):
        obj  = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task", "depends_on":["basic::sub.1", "basic::sub.2"], "required_for": ["basic::super.1"]})
        assert(not bool(obj.specs))
        obj.register_spec(spec)
        assert(bool(obj.specs))
        assert(len(obj.specs) == 2)

    def test_register_spec_ignores_disabled(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task", "disabled":True})
        assert(len(obj.specs) == 0)
        obj.register_spec(spec)
        assert(len(obj.specs) == 0)

    def test_register_partial_spec(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task", "actions":[{"do":"log", "msg":"blah"}]})
        obj.register_spec(spec)
        partial_spec = TaskSpec.build({"name":"basic::task.blah..<partial>", "sources":["basic::task"], "actions":[{"do":"log", "msg":"blah"}]})
        obj.register_spec(partial_spec)
        assert("basic::task.blah" in obj.specs)
        assert("basic::task.blah..<partial>" not in obj.specs)

class TestInstantiation:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_instantiate_spec(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        pre_count = len(obj.specs)
        assert(not bool(obj.concrete))
        match obj._instantiate_spec(TaskName("basic::task")):
            case TaskName() as x if x.is_uniq():
                assert(pre_count < len(obj.specs))
                assert(bool(obj.concrete))
            case x:
                 assert(False), x

    def test_instantiate_spec_doesnt_instance_cleanup(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        pre_count = len(obj.specs)
        assert(not bool(obj.concrete))
        instance = obj._instantiate_spec(TaskName("basic::task"))
        assert(instance in obj.specs)
        assert(not bool(obj.concrete[spec.name.with_cleanup()]))

    def test_instantiate_spec_fail(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        pre_count = len(obj.specs)
        assert(not bool(obj.concrete))
        with pytest.raises(KeyError):
            obj._instantiate_spec(TaskName("basic::bad"))

    @pytest.mark.xfail
    def test_reuse_instantiation(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        pre_count = len(obj.specs)
        assert(not bool(obj.concrete))
        inst_1 = obj._instantiate_spec(TaskName("basic::task"))
        inst_2 = obj._instantiate_spec(TaskName("basic::task"))
        assert(inst_1 == inst_2)

    def test_dont_reuse_instantiation(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        pre_count = len(obj.specs)
        assert(not bool(obj.concrete))
        inst_1 = obj._instantiate_spec(TaskName("basic::task"))
        inst_2 = obj._instantiate_spec(TaskName("basic::task"), extra={"blah":"bloo"})
        assert(inst_1 != inst_2)

    def test_instantiate_relation(self):
        obj = TrackRegistry()
        control_spec = TaskSpec.build({"name":"basic::task", "depends_on": ["basic::dep"]})
        dep_spec = TaskSpec.build({"name":"basic::dep", "actions":[{"do":"log", "msg":"blah"}]})
        obj.register_spec(control_spec, dep_spec)

        control_inst = obj._instantiate_spec(control_spec.name)
        match obj._instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                assert(dep_name.is_uniq())
                assert(dep_spec.name < dep_name)
                assert(dep_name in obj.specs)
                dep_inst_spec = obj.specs[dep_name]
                assert(bool(dep_inst_spec.actions))
            case x:
                 assert(False), x

    def test_instantiate_relation_with_injection(self):
        obj = TrackRegistry()
        dependency = {"task":"basic::dep", "inject":{"from_spec":["blah"]}}
        control_spec = TaskSpec.build({"name":"basic::task", "depends_on": [dependency], "blah": "bloo"})
        dep_spec = TaskSpec.build({"name":"basic::dep", "actions":[{"do":"log", "msg":"blah"}]})
        obj.register_spec(control_spec, dep_spec)

        control_inst = obj._instantiate_spec(control_spec.name)
        match obj._instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                dep_inst_spec = obj.specs[dep_name]
                assert(dep_inst_spec.extra["blah"] == "bloo")
            case x:
                 assert(False), x

    def test_instantiate_relation_with_late_injection(self):
        obj = TrackRegistry()
        dependency = {"task":"basic::dep", "inject":{"from_spec":["blah"], "from_state":["aweg"]}}
        control_spec = TaskSpec.build({"name":"basic::task", "depends_on": [dependency], "blah": "bloo", "aweg":"qqqq"})
        dep_spec = TaskSpec.build({"name":"basic::dep", "actions":[{"do":"log", "msg":"blah"}]})
        obj.register_spec(control_spec, dep_spec)

        control_inst = obj._instantiate_spec(control_spec.name)
        match obj._instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                dep_inst_spec = obj.specs[dep_name]
                assert(dep_inst_spec.extra["blah"] == "bloo")
                assert("aweg" not in dep_inst_spec.extra)
                assert(dep_name in obj._late_injections)
            case x:
                 assert(False), x

    def test_instantiate_relation_with_constraints(self):
        obj = TrackRegistry()
        control_spec = TaskSpec.build({"name":"basic::task",
                                                    "constraints":["blah", "aweg"],
                                                    "blah": "bloo", "aweg":"qqqq",
                                                    "depends_on": [{"task":"basic::dep", "constraints":["blah", "aweg"]}],
                                                    })
        basic_dep = TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(control_spec, basic_dep)

        control_inst = obj._instantiate_spec(control_spec.name)
        not_suitable = obj._instantiate_spec(basic_dep.name, extra={"blah":"bloo", "aweg":"BAD"})
        suitable     = obj._instantiate_spec(basic_dep.name, extra={"blah":"bloo", "aweg":"qqqq"})
        match obj._instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                assert(dep_name == suitable)
            case x:
                 assert(False), x

    def test_instantiate_relation_with_no_matching_constraints(self):
        obj = TrackRegistry()
        control_spec = TaskSpec.build({"name":"basic::task",
                                                    "constraints":["blah", "aweg"],
                                                    "blah": "bloo", "aweg":"qqqq",
                                                    "depends_on": [{"task":"basic::dep", "constraints":["blah", "aweg"]}],
                                                    })
        basic_dep = TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(control_spec, basic_dep)

        control_inst = obj._instantiate_spec(control_spec.name)
        bad_1 = obj._instantiate_spec(basic_dep.name, extra={"blah":"bloo", "aweg":"BAD"})
        bad_2 = obj._instantiate_spec(basic_dep.name, extra={"blah":"BAD", "aweg":"qqqq"})
        match obj._instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                assert(dep_name != bad_1)
                assert(dep_name != bad_1)
            case x:
                 assert(False), x

    def test_make_task(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        assert(not bool(obj.tasks))
        obj._make_task(instance)
        assert(bool(obj.tasks))

    def test_make_task_with_late_injection(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task"})
        inj  = InjectSpec.build({"from_state": ["blah"]})
        obj.register_spec(spec)
        source_inst = obj._instantiate_spec(spec.name)
        obj._make_task(source_inst)
        obj.tasks[source_inst].state["blah"] = "bloo"

        dep_inst = obj._instantiate_spec(spec.name)
        obj._register_late_injection(dep_inst, inj, source_inst)
        obj._make_task(dep_inst)
        assert("blah" in obj.tasks[dep_inst].state)
        assert(obj.tasks[dep_inst].state["blah"] == "bloo")

class TestRegistryInternals:

    def test_basic(self):
        obj = TrackRegistry()
        assert(obj is not None)

    def test_instantiate_spec_no_op(self):
        obj       = TrackRegistry()
        base_spec = TaskSpec.build({"name":"basic::task"})
        spec      = TaskSpec.build({"name":"test::spec"})
        obj.register_spec(base_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec is not special)
        assert(spec is not base_spec)
        assert(spec.name < special)
        assert(special in obj.concrete[spec.name])

    def test_instantiate_spec(self):
        obj = TrackRegistry()
        base_spec = TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        dep_spec = TaskSpec.build({"name": "example::dep"})
        spec    = TaskSpec.build({"name":"test::spec", "sources": ["basic::task"], "bloo": 15})
        obj.register_spec(base_spec, dep_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, TaskName))
        assert(special in obj.concrete[spec.name])

    @pytest.mark.xfail
    def test_instantiate_spec_match_reuse(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        obj.register_spec(spec)
        instances = set()
        for i in range(5):
            instance = obj._instantiate_spec(spec.name)
            assert(isinstance(instance, TaskName))
            assert(instance in obj.concrete[spec.name])
            instances.add(instance)
            assert(spec.name < instance)
            assert(obj.specs[instance] is not obj.specs[spec.name])
            assert(len(obj.concrete[spec.name]) == 1)
        assert(len(instances) == 1)

    def test_instantiate_job_head(self):
        obj = TrackRegistry()
        spec = TaskSpec.build({"name":"basic::task", "ctor": "doot.workflow:DootJob", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
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
        base_spec = TaskSpec.build({"name":"basic::task", "blah": 2, "bloo": 5})
        dep_spec = TaskSpec.build({"name": "example::dep", "sources": ["basic::task"], "bloo":10, "aweg":15 })
        spec    = TaskSpec.build({"name":"test::spec", "sources": ["example::dep"], "aweg": 20})
        obj.register_spec(base_spec, dep_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, TaskName))

    def test_instantiate_spec_name_change(self):
        obj       = TrackRegistry()
        base_spec = TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        dep_spec = TaskSpec.build({"name": "example::dep"})
        spec    = TaskSpec.build({"name":"test::spec", "sources": ["basic::task"], "bloo": 15})
        obj.register_spec(base_spec, dep_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, TaskName))
        assert(spec.name < special)
        assert(isinstance(special[1:-1], UUID))

    def test_instantiate_spec_extra_merge(self):
        obj           = TrackRegistry()
        base_spec     = TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        dep_spec      = TaskSpec.build({"name": "example::dep"})
        abs_spec      = TaskSpec.build({"name":"basic::task.a", "sources": ["basic::task"], "bloo": 15, "aweg": "aweg"})
        spec          = abs_spec.over(base_spec)
        obj.register_spec(base_spec, dep_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, TaskName))
        concrete = obj.specs[special]
        assert(concrete.extra.blah == 2)
        assert(concrete.extra.bloo == 15)

    def test_instantiate_spec_depends_merge(self):
        obj       = TrackRegistry()
        base_spec = TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"]})
        dep_spec  = TaskSpec.build({"name": "example::dep"})
        dep_spec2 = TaskSpec.build({"name": "another::dep"})
        spec      = base_spec.under({"depends_on":["another::dep"]})
        obj.register_spec(base_spec, dep_spec, dep_spec2, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, TaskName))
        concrete = obj.specs[special]
        assert(len(concrete.depends_on) == 2)
        assert(any("example::dep" in x.target for x in concrete.depends_on))
        assert(any("another::dep" in x.target for x in concrete.depends_on))
