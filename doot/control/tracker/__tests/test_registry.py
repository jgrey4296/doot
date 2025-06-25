#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN202, PLR2004, B011, B007
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
from ..tracker import Tracker
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
logmod.getLogger("jgdv").propagate = False

@pytest.fixture(scope="function")
def registry():
    tracker = Tracker()
    return tracker._registry

class TestRegistry:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_task_retrieval(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        name = spec.name
        registry.register_spec(spec)
        instance  = registry.instantiate_spec(name)
        result    = registry.make_task(instance)
        retrieved = registry.tasks[result]
        assert(isinstance(retrieved, Task_p))

    def test_task_get_default_status(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        name = spec.name
        registry.register_spec(spec)
        instance = registry.instantiate_spec(name)
        result   = registry.make_task(instance)
        status   = registry.get_status(result)
        assert(status is TaskStatus_e.INIT)

    def test_task_status_missing_task(self, registry):
        name = TaskName("basic::task")
        assert(registry.get_status(name) == TaskStatus_e.NAMED)

    def test_set_status(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        name = spec.name
        registry.register_spec(spec)
        instance = registry.instantiate_spec(name)
        result = registry.make_task(instance)
        assert(registry.get_status(result) is TaskStatus_e.INIT)
        assert(registry.set_status(result, TaskStatus_e.SUCCESS) is True)
        assert(registry.get_status(result) is TaskStatus_e.SUCCESS)

    def test_set_status_missing_task(self, registry):
        name = TaskName("basic::task")
        assert(registry.set_status(name, TaskStatus_e.SUCCESS) is False)

    def test_spec_retrieval(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        name = spec.name
        registry.register_spec(spec)
        retrieved = registry.specs[name]
        assert(retrieved == spec)

class TestRegistration:

    def test_sanity(self):
        assert(registry is not None)

    def test_register_spec(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        assert(not bool(registry.specs))
        registry.register_spec(spec)
        assert(bool(registry.specs))
        assert(len(registry.specs) == 1)

    def test_register_spec_adds_to_implicit(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        assert(not bool(registry.specs))
        assert(not bool(registry.implicit))
        registry.register_spec(spec)
        assert(bool(registry.specs))
        assert(bool(registry.implicit))
        assert(len(registry.specs) == 1)
        assert(registry.implicit[spec.name.with_cleanup()] == spec.name)

    def test_register_job_adds_to_implicit(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::+.job"})
        assert(not bool(registry.specs))
        assert(not bool(registry.implicit))
        registry.register_spec(spec)
        assert(bool(registry.specs))
        assert(bool(registry.implicit))
        assert(len(registry.specs) == 1)
        assert(registry.implicit[spec.name.with_head()] == spec.name)
        assert(spec.name.with_cleanup() not in registry.implicit)

    def test_register_job_head_adds_cleanup_to_implicit(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::+.job..$head$"})
        assert(not bool(registry.specs))
        assert(not bool(registry.implicit))
        registry.register_spec(spec)
        assert(bool(registry.specs))
        assert(bool(registry.implicit))
        assert(len(registry.specs) == 1)
        assert(spec.name not in registry.implicit)
        assert(spec.name.with_cleanup() in registry.implicit)

    def test_register_spec_not_implicit_extras(self, registry):
        """
        Registering a spec doesn't register implicit extras
        """
        spec = registry._tracker._factory.build({"name":"basic::task"})
        assert(not bool(registry.specs))
        registry.register_spec(spec)
        assert(spec.name.with_cleanup() not in registry.concrete)

    def test_register_job_spec_not_implicit_extras(self, registry):
        """
        Registering a job does not register extras
        """
        spec = registry._tracker._factory.build({"name":"basic::+.job"})
        assert(not bool(registry.specs))
        registry.register_spec(spec)
        assert(bool(registry.specs))
        assert(spec.name in registry.specs)
        assert(spec.name.with_head() not in registry.concrete)
        assert(spec.name.with_head() not in registry.specs)
        assert(not bool(registry.concrete[spec.name]))

    def test_register_abstract_is_idempotent(self, registry):
        """
        Re-registering a spec doesnt add it again
        """
        spec = registry._tracker._factory.build({"name":"basic::task"})
        assert(not bool(registry.specs))
        assert(not bool(registry.concrete[spec.name]))
        assert(len(registry.specs) == 0)
        for _ in range(5):
            registry.register_spec(spec)
            assert(len(registry.specs) == 1) # just the spec
            assert(len(registry.concrete[spec.name]) == 0) # no concrete

    def test_re_registration_errors_on_overwrite(self, registry):
        """
        Re-registering a spec doesnt add it again
        """
        spec  = registry._tracker._factory.build({"name":"basic::task"})
        spec2 = registry._tracker._factory.build({"name":"basic::task", "blah": "bloo"})
        assert(not bool(registry.specs))
        assert(not bool(registry.concrete[spec.name]))
        assert(len(registry.specs) == 0)
        registry.register_spec(spec)
        assert("blah" not in registry.specs[spec.name].extra)
        with pytest.raises(ValueError):
            registry.register_spec(spec2)

    def test_register_concrete_is_idempotent(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        ispec = registry._tracker._factory.instantiate(spec)
        assert(not bool(registry.specs))
        assert(not bool(registry.concrete[ispec.name]))
        assert(len(registry.specs) == 0)
        for _ in range(5):
            registry.register_spec(ispec)
            assert(len(registry.specs) == 2) # just the spec and its cleanup
            assert(len(registry.concrete[ispec.name.de_uniq()]) == 1) # no concrete

    def test_register_spec_with_artifacts(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task",
                               "depends_on":["file::>test.txt"],
                               "required_for": ["file::>other.txt"]})
        assert(not bool(registry.artifacts))
        registry.register_spec(spec)
        assert(bool(registry.artifacts))
        assert(len(registry.artifacts) == 2)

    def test_register_abstract_spec_adds_no_dependencies(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task",
                               "depends_on":["basic::sub.1", "basic::sub.2"],
                               "required_for": ["basic::super.1"]})
        assert(not bool(registry.specs))
        registry.register_spec(spec)
        assert(bool(registry.specs))
        assert(len(registry.specs) == 1)
        assert("basic::task" in registry.specs)
        assert("basic::sub.1" not in registry.specs)
        assert("basic::super.1" not in registry.specs)

    def test_register_concrete_spec_adds_subtasks(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task",
                               "depends_on":["basic::sub.1", "basic::sub.2"],
                               "required_for": ["basic::super.1"]})
        ispec = registry._tracker._factory.instantiate(spec)
        assert(not bool(registry.specs))
        registry.register_spec(ispec)
        assert(bool(registry.specs))
        assert(len(registry.specs) == 2)

    def test_register_spec_ignores_disabled(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task", "disabled":True})
        assert(len(registry.specs) == 0)
        registry.register_spec(spec)
        assert(len(registry.specs) == 0)

    @pytest.mark.xfail
    def test_register_partial_spec(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task", "actions":[{"do":"log", "msg":"blah"}]})
        registry.register_spec(spec)
        partial_spec = registry._tracker._factory.build({"name":"basic::task.blah..$partial$", "sources":["basic::task"], "actions":[{"do":"log", "msg":"blah"}]})
        registry.register_spec(partial_spec)
        assert("basic::task.blah" in registry.specs)
        assert("basic::task.blah..$partial$" not in registry.specs)

class TestInstantiation_Specs:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_instantiate_spec(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        registry.register_spec(spec)
        pre_count = len(registry.specs)
        assert(not bool(registry.concrete))
        match registry.instantiate_spec(TaskName("basic::task")):
            case TaskName() as x if x.uuid():
                assert(pre_count < len(registry.specs))
                assert(bool(registry.concrete))
            case x:
                 assert(False), x

    @pytest.mark.xfail
    def test_instantiate_spec_instances_cleanup(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        registry.register_spec(spec)
        pre_count = len(registry.specs)
        assert(not bool(registry.concrete))
        instance = registry.instantiate_spec(TaskName("basic::task"))
        assert(instance in registry.specs)
        assert(bool(registry.concrete[spec.name.with_cleanup()]))

    def test_instantiate_spec_fail(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        registry.register_spec(spec)
        pre_count = len(registry.specs)
        assert(not bool(registry.concrete))
        with pytest.raises(KeyError):
            registry.instantiate_spec(TaskName("basic::bad"))

    def test_reuse_instantiation(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        registry.register_spec(spec)
        pre_count = len(registry.specs)
        assert(not bool(registry.concrete))
        inst_1 = registry.instantiate_spec(TaskName("basic::task"))
        inst_2 = registry.instantiate_spec(TaskName("basic::task"))
        assert(inst_1 == inst_2)

    def test_dont_reuse_instantiation(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        registry.register_spec(spec)
        pre_count = len(registry.specs)
        assert(not bool(registry.concrete))
        inst_1 = registry.instantiate_spec(TaskName("basic::task"))
        inst_2 = registry.instantiate_spec(TaskName("basic::task"), extra={"blah":"bloo"})
        assert(inst_1 != inst_2)

    def test_instantiate_spec_no_op(self, registry):
        base_spec = registry._tracker._factory.build({"name":"basic::task"})
        spec      = registry._tracker._factory.build({"name":"test::spec"})
        registry.register_spec(base_spec, spec)
        special = registry.instantiate_spec(spec.name)
        assert(spec is not special)
        assert(spec is not base_spec)
        assert(spec.name < special)
        assert(special in registry.concrete[spec.name])

    def test_instantiate_spec_match_reuse(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        registry.register_spec(spec)
        instances = set()
        for i in range(5):
            instance = registry.instantiate_spec(spec.name)
            assert(isinstance(instance, TaskName))
            assert(instance in registry.concrete[spec.name])
            instances.add(instance)
            assert(spec.name < instance)
            assert(registry.specs[instance] is not registry.specs[spec.name])
            assert(len(registry.concrete[spec.name]) == 1)
        assert(len(instances) == 1)

    def test_instantiate_spec_chain(self, registry):
        base_spec = registry._tracker._factory.build({"name":"basic::task", "blah": 2, "bloo": 5})
        dep_spec  = registry._tracker._factory.build({"name": "example::dep", "sources": ["basic::task"], "bloo":10, "aweg":15 })
        spec      = registry._tracker._factory.build({"name":"test::spec", "sources": ["example::dep"], "aweg": 20})
        registry.register_spec(base_spec, dep_spec, spec)
        special = registry.instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, TaskName))

    def test_instantiate_spec_name_change(self, registry):
        spec      = registry._tracker._factory.build({"name":"test::spec",
                                    "sources": ["basic::task"], "bloo": 15})
        base_spec = registry._tracker._factory.build({"name":"basic::task",
                                    "depends_on":["example::dep"],
                                    "blah": 2, "bloo": 5})
        dep_spec  = registry._tracker._factory.build({"name": "example::dep"})
        registry.register_spec(base_spec, dep_spec, spec)
        special = registry.instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, TaskName))
        assert(spec.name < special)
        assert(special.uuid())

    def test_instantiate_spec_extra_merge(self, registry):
        base_spec     = registry._tracker._factory.build({"name":"basic::task",
                                        "depends_on":["example::dep"],
                                        "blah": 2, "bloo": 5})
        dep_spec      = registry._tracker._factory.build({"name": "example::dep"})
        abs_spec      = registry._tracker._factory.build({"name":"basic::task.a",
                                        "sources": ["basic::task"],
                                        "bloo": 15, "aweg": "aweg"})
        spec          = registry._tracker._factory.merge(top=abs_spec, bot=base_spec)
        registry.register_spec(base_spec, dep_spec, spec)
        special = registry.instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, TaskName))
        concrete = registry.specs[special]
        assert(concrete.extra.blah == 2)
        assert(concrete.extra.bloo == 15)

    def test_instantiate_spec_depends_merge(self, registry):
        base_spec = registry._tracker._factory.build({"name":"basic::task", "depends_on":["example::dep"]})
        dep_spec  = registry._tracker._factory.build({"name": "example::dep"})
        dep_spec2 = registry._tracker._factory.build({"name": "another::dep"})
        spec      = registry._tracker._factory.merge(bot=base_spec, top={"depends_on":["another::dep"]})
        registry.register_spec(base_spec, dep_spec, dep_spec2, spec)
        special = registry.instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, TaskName))
        concrete = registry.specs[special]
        assert(len(concrete.depends_on) == 2)
        assert(any("example::dep" in x.target for x in concrete.depends_on))
        assert(any("another::dep" in x.target for x in concrete.depends_on))

class TestInstantiation_Jobs:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_instantiate_job(self, registry):
        spec     = registry._tracker._factory.build({"name":"basic::+.job",
                                   "depends_on":["example::dep"],
                                   "blah": 2, "bloo": 5})
        abs_head = spec.name.with_head()
        registry.register_spec(spec)
        assert(abs_head not in registry.concrete)
        instance = registry.instantiate_spec(spec.name)
        assert(instance in registry.specs)
        assert(abs_head in registry.concrete)
        assert(registry.concrete[abs_head][0] in registry.specs)
        assert(instance in registry.concrete[spec.name])
        assert(spec.name < instance)

    def test_instantiate_job_head(self, registry):
        spec     = registry._tracker._factory.build({"name":"basic::+.job",
                                   "depends_on":["example::dep"],
                                   "blah": 2, "bloo": 5})
        abs_head = spec.name.with_head()
        registry.register_spec(spec)
        assert(abs_head not in registry.concrete)
        instance = registry.instantiate_spec(spec.name)
        assert(instance in registry.specs)
        assert(abs_head in registry.concrete)
        assert(registry.concrete[abs_head][0] in registry.specs)
        assert(instance in registry.concrete[spec.name])
        assert(spec.name < instance)

    @pytest.mark.xfail
    def test_instantiate_job_cleanup(self, registry):
        spec     = registry._tracker._factory.build({"name":"basic::+.job",
                                   "depends_on":["example::dep"],
                                   "blah": 2, "bloo": 5})
        ##--|
        spec_cleanup = spec.name.with_cleanup()
        abs_head     = spec.name.with_head()
        head_cleanup = spec.name.with_head().with_cleanup()
        registry.register_spec(spec)
        # Only the spec is registered
        assert(abs_head not in registry.specs)
        assert(spec_cleanup not in registry.specs)
        assert(abs_head not in registry.concrete)
        assert(spec_cleanup not in registry.concrete)
        instance = registry.instantiate_spec(spec.name)
        assert(instance in registry.specs)
        # After instantiation, the head is registered, cleanup isnt
        assert(abs_head in registry.concrete)
        assert(spec_cleanup not in registry.specs)
        assert(spec_cleanup not in registry.concrete)
        assert(registry.concrete[abs_head][0] in registry.specs)
        assert(instance in registry.concrete[spec.name])
        assert(spec.name < instance)

class TestInstantiation_Relations:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_relation(self, registry):
        control_spec = registry._tracker._factory.build({"name":"basic::task", "depends_on": ["basic::dep"]})
        dep_spec = registry._tracker._factory.build({"name":"basic::dep", "actions":[{"do":"log", "msg":"blah"}]})
        registry.register_spec(control_spec, dep_spec)

        control_inst = registry.instantiate_spec(control_spec.name)
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                assert(dep_name.uuid())
                assert(dep_spec.name < dep_name)
                assert(dep_name in registry.specs)
                dep_inst_spec = registry.specs[dep_name]
                assert(bool(dep_inst_spec.actions))
            case x:
                 assert(False), x

    def test_relation_with_injection(self, registry):
        dependency = {"task":"basic::dep", "inject":{"from_spec":["blah"]}}
        control_spec = registry._tracker._factory.build({"name":"basic::task", "depends_on": [dependency], "blah": "bloo"})
        dep_spec = registry._tracker._factory.build({"name":"basic::dep", "actions":[{"do":"log", "msg":"blah"}]})
        registry.register_spec(control_spec, dep_spec)

        control_inst = registry.instantiate_spec(control_spec.name)
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                dep_inst_spec = registry.specs[dep_name]
                assert(dep_inst_spec.extra["blah"] == "bloo")
            case x:
                 assert(False), x

    def test_relation_with_late_injection(self, registry):
        dependency = {"task":"basic::dep", "inject":{"from_spec":["blah"], "from_state":["aweg"]}}
        control_spec = registry._tracker._factory.build({"name":"basic::task", "depends_on": [dependency], "blah": "bloo", "aweg":"qqqq"})
        dep_spec = registry._tracker._factory.build({"name":"basic::dep", "actions":[{"do":"log", "msg":"blah"}]})
        registry.register_spec(control_spec, dep_spec)

        control_inst = registry.instantiate_spec(control_spec.name)
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                dep_inst_spec = registry.specs[dep_name]
                assert(dep_inst_spec.extra["blah"] == "bloo")
                assert("aweg" not in dep_inst_spec.extra)
                assert(dep_name in registry.late_injections)
            case x:
                 assert(False), x

    @pytest.mark.xfail
    def test_relation_with_constraints(self, registry):
        relation = {"task":"basic::dep", "constraints":["blah", "aweg"]}
        control_spec = registry._tracker._factory.build({"name":"basic::task",
                                       "blah": "bloo", "aweg":"qqqq",
                                       "depends_on": [relation],
                                       })
        basic_dep = registry._tracker._factory.build({"name":"basic::dep"})
        registry.register_spec(control_spec, basic_dep)

        control_inst = registry.instantiate_spec(control_spec.name)
        not_suitable = registry.instantiate_spec(basic_dep.name, extra={"blah":"bloo", "aweg":"BAD"})
        suitable     = registry.instantiate_spec(basic_dep.name, extra={"blah":"bloo", "aweg":"qqqq"})
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                assert(dep_name == suitable)
            case x:
                 assert(False), x

    def test_relation_with_no_matching_constraints(self, registry):
        control_spec = registry._tracker._factory.build({"name":"basic::task",
                                       "blah": "bloo", "aweg":"qqqq",
                                       "depends_on": [{"task":"basic::dep", "constraints":["blah", "aweg"]}],
                                       })
        basic_dep = registry._tracker._factory.build({"name":"basic::dep"})
        registry.register_spec(control_spec, basic_dep)

        control_inst = registry.instantiate_spec(control_spec.name)
        bad_1        = registry.instantiate_spec(basic_dep.name, extra={"blah":"bloo", "aweg":"BAD"})
        bad_2        = registry.instantiate_spec(basic_dep.name, extra={"blah":"BAD", "aweg":"qqqq"})
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                assert(dep_name != bad_1)
                assert(dep_name != bad_2)
            case x:
                 assert(False), x

    def test_relation_with_no_matching_spec_errors(self, registry):
        control_spec = registry._tracker._factory.build({"name":"basic::task",
                                       "blah": "bloo", "aweg":"qqqq",
                                       "depends_on": [{"task":"basic::dep", "constraints":["blah", "aweg"]}],
                                       })
        registry.register_spec(control_spec)

        control_inst = registry.instantiate_spec(control_spec.name)
        with pytest.raises(doot.errors.TrackingError):
            registry.instantiate_relation(control_spec.depends_on[0],
                                      control=control_inst)

    def test_relation_with_no_matching_control_spec_errors(self, registry):
        control_spec = registry._tracker._factory.build({"name":"basic::task",
                                       "blah": "bloo", "aweg":"qqqq",
                                       "depends_on": [{"task":"basic::dep"}],
                                       })

        control_inst = control_spec.name.to_uniq()
        with pytest.raises(doot.errors.TrackingError):
            registry.instantiate_relation(control_spec.depends_on[0],
                                      control=control_inst)

    @pytest.mark.xfail
    def test_relation_with_uniq_target(self, registry):
        target_spec = registry._tracker._factory.build({"name":"basic::target"})
        registry.register_spec(target_spec)
        target_inst = registry.instantiate_spec(target_spec.name)
        control_spec = registry._tracker._factory.build({"name":"basic::task",
                                       "blah": "bloo", "aweg":"qqqq",
                                       "depends_on": [{"task":target_inst}],
                                       })
        registry.register_spec(control_spec)
        control_inst = registry.instantiate_spec(control_spec.name)
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as x if x == target_inst:
                assert(True)
            case x:
                 assert(False), x

    @pytest.mark.xfail
    def test_relation_with_reuse_injection(self, registry):
        target_spec = registry._tracker._factory.build({"name":"basic::target"})
        registry.register_spec(target_spec)
        target_inst_1 = registry.instantiate_spec(target_spec.name,
                                              extra={"blah":"bloo"})
        target_inst_2 = registry.instantiate_spec(target_spec.name,
                                              extra={"blah":"aweg"})
        relation = {"task":"basic::target", "inject":{"from_spec":["blah"]}}
        control_spec = registry._tracker._factory.build({"name":"basic::control",
                                       "blah": "aweg",
                                       "depends_on": [relation]})
        registry.register_spec(control_spec)
        control_inst = registry.instantiate_spec(control_spec.name)
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as x if x == target_inst_2:
                assert(True)
            case x:
                assert(False), x

    def test_relation_without_reusing_injection(self, registry):
        target_spec = registry._tracker._factory.build({"name":"basic::target"})
        registry.register_spec(target_spec)
        target_inst_1 = registry.instantiate_spec(target_spec.name,
                                              extra={"blah":"bloo"})
        target_inst_2 = registry.instantiate_spec(target_spec.name,
                                              extra={"blah":"qqqq"})
        relation = {"task":"basic::target", "inject":{"from_spec":["blah"]}}
        control_spec = registry._tracker._factory.build({"name":"basic::control",
                                       "blah": "aweg",
                                       "depends_on": [relation]})
        registry.register_spec(control_spec)
        control_inst = registry.instantiate_spec(control_spec.name)
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as x if x not in [target_inst_1, target_inst_2]:
                assert(True)
            case x:
                assert(False), x

    def test_relation_with_job_head(self, registry):
        target_spec = registry._tracker._factory.build({"name":"basic::+.target"})
        registry.register_spec(target_spec)
        relation = {"task":"basic::+.target..$head$"}
        control_spec = registry._tracker._factory.build({"name":"basic::control",
                                       "blah": "aweg",
                                       "depends_on": [relation]})
        registry.register_spec(control_spec)
        control_inst = registry.instantiate_spec(control_spec.name)
        # First instantiate the base job relation
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as x if "basic::+.target" < x and not x.is_head():
                assert(True)
            case x:
                assert(False), x
        # Then the head
        registry.instantiate_spec(target_spec.name.with_head())
        match registry.instantiate_relation(control_spec.depends_on[1], control=control_inst):
            case TaskName() as x if "basic::+.target" < x and x.is_head():
                assert(True)
            case x:
                assert(False), x

class TestInstantiation_Tasks:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_make_task(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        name = spec.name
        registry.register_spec(spec)
        instance = registry.instantiate_spec(name)
        assert(not bool(registry.tasks))
        registry.make_task(instance)
        assert(bool(registry.tasks))

    def test_make_task_with_late_injection(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        inj  = InjectSpec.build({"from_state": ["blah"]})
        registry.register_spec(spec)
        source_inst = registry.instantiate_spec(spec.name)
        registry.make_task(source_inst)
        registry.tasks[source_inst].state["blah"] = "bloo"

        dep_inst = registry.instantiate_spec(spec.name)
        registry._register_late_injection(dep_inst, inj, source_inst)
        registry.make_task(dep_inst)
        assert("blah" in registry.tasks[dep_inst].state)
        assert(registry.tasks[dep_inst].state["blah"] == "bloo")
