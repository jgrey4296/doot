#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN202, PLR2004, B011, B007, ANN001
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
from doot.workflow._interface import TaskStatus_e, TaskName_p
from doot.workflow import TaskName, TaskSpec, InjectSpec

# ##-- end 1st party imports

# ##-| Local
from .. import _interface as API # noqa: N812
from ..naive_tracker import NaiveTracker
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
logmod.getLogger("doot.util").propagate = False

@pytest.fixture(scope="function")
def registry():
    tracker = NaiveTracker()
    return tracker._registry


class TestRegistry:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        assert(isinstance(TrackRegistry, API.Registry_p))

class TestRegistration:

    def test_sanity(self):
        assert(registry is not None)

    def test_register_spec(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        assert(not bool(registry.specs))
        registry.register_spec(spec)
        assert(bool(registry.specs))
        assert(len(registry.specs) == 1)

    def test_register_spec_adds_to_abstract(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        assert(not bool(registry.abstract))
        registry.register_spec(spec)
        assert(bool(registry.abstract))

    def test_register_job_only_adds_a_single_spec(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::+.job"})
        assert(not bool(registry.specs))
        registry.register_spec(spec)
        assert(len(registry.specs) == 1)

    def test_register_abstract_is_idempotent(self, registry):
        """
        Re-registering a spec doesnt add it again
        """
        spec = registry._tracker._factory.build({"name":"basic::task"})
        assert(not bool(registry.specs))
        assert(not bool(registry.concrete))
        assert(not bool(registry.abstract))
        assert(len(registry.specs) == 0)
        for _ in range(5):
            registry.register_spec(spec)
            assert(len(registry.specs) == 1) # just the spec
            assert(len(registry.concrete) == 0) # no concrete
            assert(len(registry.abstract) == 1) # no concrete

    def test_re_registration_errors_on_overwrite(self, registry):
        """
        Re-registering a spec doesnt add it again
        """
        spec  = registry._tracker._factory.build({"name":"basic::task"})
        spec2 = registry._tracker._factory.build({"name":"basic::task", "blah": "bloo"})
        assert(not bool(registry.specs))
        assert(not bool(registry.concrete))
        assert(len(registry.specs) == 0)
        registry.register_spec(spec)
        assert("blah" not in registry.specs[spec.name].spec.extra)
        with pytest.raises(ValueError):
            registry.register_spec(spec2)

        assert("blah" not in registry.specs[spec.name].spec.extra)

    def test_register_concrete_is_idempotent(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        ispec = registry._tracker._factory.instantiate(spec)
        assert(not bool(registry.specs))
        assert(not bool(registry.concrete))
        registry.register_spec(spec)
        assert(len(registry.specs) == 1)
        for _ in range(5):
            registry.register_spec(ispec)
            assert(len(registry.specs) == 2)
            assert(len(registry.concrete) == 1) # no concrete
        else:
            assert(registry.specs[spec.name].related == {ispec.name})

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

    def test_register_concrete_spec_adds_no_subtasks(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task",
                               "depends_on":["basic::sub.1", "basic::sub.2"],
                               "required_for": ["basic::super.1"]})
        ispec = registry._tracker._factory.instantiate(spec)
        assert(not bool(registry.specs))
        registry.register_spec(spec)
        registry.register_spec(ispec)
        assert(bool(registry.specs))
        assert(len(registry.specs) == 2)

    def test_register_spec_ignores_disabled(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task", "disabled":True})
        assert(len(registry.specs) == 0)
        registry.register_spec(spec)
        assert(len(registry.specs) == 0)

    def test_register_explicit_generated_task(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::+.job"})
        head = registry._tracker._factory.build({"name":"basic::+.job..$head$"})
        assert(len(registry.specs) == 0)
        registry.register_spec(spec)
        assert(len(registry.specs) == 1)
        registry.register_spec(head)
        assert(len(registry.specs) == 2)
        assert(head.name in registry.specs)

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
        assert(inst_1.uuid() == inst_2.uuid())

    def test_dont_reuse_instantiation(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        registry.register_spec(spec)
        pre_count = len(registry.specs)
        assert(not bool(registry.concrete))
        inst_1 = registry.instantiate_spec(TaskName("basic::task"))
        inst_2 = registry.instantiate_spec(TaskName("basic::task"), extra={"blah":"bloo"})
        assert(inst_1 != inst_2)
        assert(inst_1.uuid() != inst_2.uuid())

    def test_instantiation_force_new(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        registry.register_spec(spec)
        pre_count = len(registry.specs)
        assert(not bool(registry.concrete))
        inst_1 = registry.instantiate_spec(TaskName("basic::task"))
        inst_2 = registry.instantiate_spec(TaskName("basic::task"), force=True)
        assert(inst_1 != inst_2)
        assert(inst_1.uuid() != inst_2.uuid())

    def test_instantiation_disallow_new(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        registry.register_spec(spec)
        pre_count = len(registry.specs)
        assert(not bool(registry.concrete))
        inst_1 = registry.instantiate_spec(TaskName("basic::task"))
        inst_2 = registry.instantiate_spec(TaskName("basic::task"), force=False)
        assert(inst_1 == inst_2)
        assert(inst_1.uuid() == inst_2.uuid())

    def test_instantiate_spec_no_op(self, registry):
        base_spec = registry._tracker._factory.build({"name":"basic::task"})
        spec      = registry._tracker._factory.build({"name":"test::spec"})
        registry.register_spec(base_spec)
        registry.register_spec(spec)
        special = registry.instantiate_spec(spec.name)
        assert(special.uuid())
        assert(spec.name is not special)
        assert(spec is not base_spec)
        assert(spec.name < special)
        assert(special.de_uniq() in registry.concrete)
        assert(special in registry.specs[spec.name].related)

    def test_instantiate_spec_match_reuse(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        registry.register_spec(spec)
        instances = set()
        for i in range(5):
            instance = registry.instantiate_spec(spec.name)
            assert(isinstance(instance, TaskName))
            assert(instance.de_uniq() in registry.concrete)
            instances.add(instance)
            assert(spec.name < instance)
            assert(registry.specs[instance] is not registry.specs[spec.name])
            assert(len(registry.concrete) == 1)
        assert(len(instances) == 1)

    def test_instantiate_spec_chain(self, registry):
        base_spec = registry._tracker._factory.build({"name":"basic::task", "blah": 2, "bloo": 5})
        dep_spec  = registry._tracker._factory.build({"name": "example::dep", "sources": ["basic::task"], "bloo":10, "aweg":15 })
        spec      = registry._tracker._factory.build({"name":"test::spec", "sources": ["example::dep"], "aweg": 20})
        registry.register_spec(base_spec)
        registry.register_spec(dep_spec)
        registry.register_spec(spec)
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
        registry.register_spec(base_spec)
        registry.register_spec(dep_spec)
        registry.register_spec(spec)
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
        registry.register_spec(base_spec)
        registry.register_spec(dep_spec)
        registry.register_spec(spec)
        special = registry.instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, TaskName))
        concrete = registry.specs[special]
        assert(concrete.spec.extra.blah == 2)
        assert(concrete.spec.extra.bloo == 15)

    def test_instantiate_spec_depends_merge(self, registry):
        base_spec = registry._tracker._factory.build({"name":"basic::task", "depends_on":["example::dep"]})
        dep_spec  = registry._tracker._factory.build({"name": "example::dep"})
        dep_spec2 = registry._tracker._factory.build({"name": "another::dep"})
        spec      = registry._tracker._factory.merge(bot=base_spec, top={"depends_on":["another::dep"]})
        registry.register_spec(base_spec)
        registry.register_spec(dep_spec)
        registry.register_spec(dep_spec2)
        registry.register_spec(spec)
        special = registry.instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, TaskName))
        match registry.specs[special]:
            case API.SpecMeta_d(spec=_spec):
                assert(len(_spec.depends_on) == 2)
                assert(any("example::dep" in x.target for x in _spec.depends_on))
                assert(any("another::dep" in x.target for x in _spec.depends_on))
            case x:
                assert(False), x

class TestInstantiation_Jobs:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_instantiate_job(self, registry):
        """ registry instantiation  """
        spec     = registry._tracker._factory.build({"name":"basic::+.job",
                                                     "depends_on":["example::dep"],
                                                     "blah": 2, "bloo": 5})
        registry.register_spec(spec)
        instance = registry.instantiate_spec(spec.name)
        assert(instance in registry.specs)
        assert(spec.name in registry.concrete)
        assert(spec.name < instance)
        match registry.specs[spec.name]:
            case API.SpecMeta_d() as _meta:
                assert(instance in _meta.related)
            case x:
                assert(False), x

    def test_instantiate_job_head(self, registry):
        spec     = registry._tracker._factory.build({"name":"basic::+.job",
                                                     "depends_on":["example::dep"],
                                                     "blah": 2, "bloo": 5})
        registry.register_spec(spec)
        instance = registry.instantiate_spec(spec.name)
        head_inst = instance.with_head()
        assert(instance in registry.specs)
        assert(spec.name in registry.concrete)
        assert(instance in registry.specs[spec.name].related)
        assert(head_inst in registry.specs[instance].related)

    def test_instantiate_explicit_job_head(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::+.job"})
        head = registry._tracker._factory.build({"name":"basic::+.job..$head$",
                                                 "blah": 2, "bloo": 5})
        registry.register_spec(spec)
        registry.register_spec(head)
        assert(spec.name in registry.specs)
        assert(head.name in registry.specs)
        instance   = registry.instantiate_spec(spec.name)
        inst_head  = instance.with_head()
        assert(instance in registry.specs)
        assert(inst_head in registry.specs)
        assert(head.name < inst_head)
        assert(registry.instantiate_spec(inst_head) == inst_head)
        assert(inst_head in registry.specs[head.name].related)
        assert(inst_head in registry.specs[instance].related)

    def test_instantiate_job_cleanup(self, registry):
        spec     = registry._tracker._factory.build({"name":"basic::+.job",
                                                     "depends_on":["example::dep"],
                                                     "blah": 2, "bloo": 5})
        registry.register_spec(spec)
        # Only the spec is registered
        assert(len(registry.specs) == 1)
        # create the job
        instance      = registry.instantiate_spec(spec.name)
        assert(instance in registry.specs)
        assert(instance in registry.specs[spec.name].related)
        # which creates the head
        inst_head     = instance.with_head()
        assert(inst_head in registry.specs)
        assert(inst_head in registry.specs[instance].related)
        # which creates the head cleanup
        good_cleanup  = inst_head.with_cleanup()
        assert(good_cleanup in registry.specs)
        assert(good_cleanup in registry.specs[inst_head].related)
        # the job base does *not* create a cleanup
        bad_cleanup   = instance.with_cleanup()
        assert(bad_cleanup not in registry.specs)
        # In total, 4 specs
        assert(len(registry.specs) == 4)

class TestInstantiation_Relations:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_relation(self, registry):
        control_spec = registry._tracker._factory.build({"name":"basic::task", "depends_on": ["basic::dep"]})
        dep_spec = registry._tracker._factory.build({"name":"basic::dep", "actions":[{"do":"log", "msg":"blah"}]})
        registry.register_spec(control_spec)
        registry.register_spec(dep_spec)

        control_inst = registry.instantiate_spec(control_spec.name)
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                assert(dep_name.uuid())
                assert(dep_spec.name < dep_name)
                assert(dep_name in registry.specs)
                dep_inst_meta = registry.specs[dep_name]
                assert(bool(dep_inst_meta.spec.actions))
            case x:
                 assert(False), x

    def test_relation_with_injection(self, registry):
        dependency = {"task":"basic::dep", "inject":{"from_spec":["blah"]}}
        control_spec = registry._tracker._factory.build({"name":"basic::task", "depends_on": [dependency], "blah": "bloo"})
        dep_spec = registry._tracker._factory.build({"name":"basic::dep", "actions":[{"do":"log", "msg":"blah"}]})
        registry.register_spec(control_spec)
        registry.register_spec(dep_spec)

        control_inst = registry.instantiate_spec(control_spec.name)
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                dep_inst_meta = registry.specs[dep_name]
                assert("blah" in dep_inst_meta.spec.extra)
                assert(dep_inst_meta.injection_source[0] == control_inst)
            case x:
                 assert(False), x

    def test_relation_with_late_injection(self, registry):
        dependency = {"task":"basic::dep", "inject":{"from_spec":["blah"], "from_state":["aweg"]}}
        control_spec = registry._tracker._factory.build({"name":"basic::task", "depends_on": [dependency], "blah": "bloo", "aweg":"qqqq"})
        dep_spec = registry._tracker._factory.build({"name":"basic::dep", "actions":[{"do":"log", "msg":"blah"}]})
        registry.register_spec(control_spec)
        registry.register_spec(dep_spec)

        control_inst = registry.instantiate_spec(control_spec.name)
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                dep_inst_meta = registry.specs[dep_name]
                assert("blah" in dep_inst_meta.spec.extra)
                assert("aweg" not in dep_inst_meta.spec.extra)
                assert(dep_inst_meta.injection_source[0] == control_inst)
            case x:
                 assert(False), x

    def test_relation_with_constraints(self, registry):
        relation      = {"task":"basic::dep", "constraints":["blah", "aweg"]}
        basic_dep     = registry._tracker._factory.build({"name":"basic::dep"})
        control_spec  = registry._tracker._factory.build({"name":"basic::task",
                                                          "blah": "bloo", "aweg":"qqqq",
                                                          "depends_on": [relation],
                                                          })
        registry.register_spec(control_spec)
        registry.register_spec(basic_dep)

        assert(not bool(registry.concrete))
        control_inst = registry.instantiate_spec(control_spec.name)
        assert(bool(registry.concrete))
        logging.debug("Making Not Suitable")
        not_suitable = registry.instantiate_spec(basic_dep.name, extra={"blah":"bloo", "aweg":"BAD"})
        logging.debug("Making Suitable")
        suitable     = registry.instantiate_spec(basic_dep.name, extra={"blah":"bloo", "aweg":"qqqq"})
        logging.debug("Trying to reuse")
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                assert(suitable == dep_name)
            case x:
                 assert(False), x

    def test_relation_with_no_matching_constraints(self, registry):
        control_spec = registry._tracker._factory.build({"name":"basic::task",
                                       "blah": "bloo", "aweg":"qqqq",
                                       "depends_on": [{"task":"basic::dep", "constraints":["blah", "aweg"]}],
                                       })
        basic_dep = registry._tracker._factory.build({"name":"basic::dep"})
        registry.register_spec(control_spec)
        registry.register_spec(basic_dep)

        control_inst = registry.instantiate_spec(control_spec.name)
        bad_1        = registry.instantiate_spec(basic_dep.name, extra={"blah":"bloo", "aweg":"BAD"})
        bad_2        = registry.instantiate_spec(basic_dep.name, extra={"blah":"BAD", "aweg":"qqqq"})
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as dep_name:
                assert(dep_name not in [bad_1, bad_2])
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
        assert(target_inst in registry.specs)
        match registry.instantiate_relation(control_spec.depends_on[0], control=control_inst):
            case TaskName() as x if x == target_inst:
                assert(True)
            case x:
                 assert(False), x

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

    def test_relation_with_literal_job_head(self, registry):
        relation_literal  = {"task":"basic::+.target..$head$"}
        control_spec      = registry._tracker._factory.build({"name":"basic::control",
                                                              "blah": "aweg",
                                                              "depends_on": [relation_literal]})
        target_spec       = registry._tracker._factory.build({"name":"basic::+.target"})
        literal_head      = registry._tracker._factory.build({"name":"basic::+.target..$head$"})
        base_relation     = control_spec.depends_on[0]
        cleanup_relation  = control_spec.depends_on[1]
        registry.register_spec(control_spec)
        registry.register_spec(target_spec)
        registry.register_spec(literal_head)
        # instantiate the control
        control_inst = registry.instantiate_spec(control_spec.name)
        assert(control_inst in registry.specs[control_spec.name].related)
        # and the job
        job_inst = registry.instantiate_spec(target_spec.name)
        assert(job_inst in registry.specs[target_spec.name].related)
        # which instantiates the job_head and cleanup
        job_head = job_inst.with_head()
        assert(job_head in registry.specs)
        assert(job_head in registry.specs[job_inst].related)
        job_clean = job_head.with_cleanup()
        assert(job_clean in registry.specs)
        assert(job_clean in registry.specs[job_head].related)

        # instantiate the control->target relation
        rel_inst1 = registry.instantiate_relation(base_relation, control=control_inst)
        assert(rel_inst1 == job_inst)
        rel_inst2 = registry.instantiate_relation(cleanup_relation, control=control_inst)
        assert(rel_inst2 == job_head)


    def test_relation_with_literal_cleanup(self, registry):
        relation_literal  = {"task":"basic::target..$cleanup$"}
        control_spec      = registry._tracker._factory.build({"name":"basic::control",
                                                              "blah": "aweg",
                                                              "depends_on": [relation_literal]})
        target_spec       = registry._tracker._factory.build({"name":"basic::target"})
        literal_head      = registry._tracker._factory.build({"name":"basic::target..$cleanup$"})
        base_relation     = control_spec.depends_on[0]
        cleanup_relation  = control_spec.depends_on[1]
        registry.register_spec(control_spec)
        registry.register_spec(target_spec)
        registry.register_spec(literal_head)
        # instantiate the control
        control_inst = registry.instantiate_spec(control_spec.name)
        assert(control_inst in registry.specs[control_spec.name].related)
        # and the target
        target_inst = registry.instantiate_spec(target_spec.name)
        assert(target_inst in registry.specs[target_spec.name].related)
        # which instantiates the cleanup
        target_cleanup = target_inst.with_cleanup()
        assert(target_cleanup in registry.specs)
        assert(target_cleanup in registry.specs[target_inst].related)

        # instantiate the control->target relation
        rel_inst1 = registry.instantiate_relation(base_relation, control=control_inst)
        assert(rel_inst1 == target_inst)
        rel_inst2 = registry.instantiate_relation(cleanup_relation, control=control_inst)
        assert(rel_inst2 == target_cleanup)

class TestInstantiation_Tasks:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_make_task(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        name = spec.name
        registry.register_spec(spec)
        instance = registry.instantiate_spec(name)
        match registry.specs[instance]:
            case API.SpecMeta_d(task=TaskStatus_e()):
                assert(True)
            case x:
                assert(False), x
        registry.make_task(instance)
        match registry.specs[instance]:
            case API.SpecMeta_d(task=Task_p()):
                assert(True)
            case x:
                assert(False), x

    def test_make_task_with_late_injection(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        inj  = InjectSpec.build({"from_state": ["blah"]})
        registry.register_spec(spec)
        source_inst = registry.instantiate_spec(spec.name)
        registry.make_task(source_inst)
        registry.specs[source_inst].task.internal_state["blah"] = "bloo"

        dep_inst = registry.instantiate_spec(spec.name)
        registry._register_late_injection(dep_inst, inj, source_inst)
        registry.make_task(dep_inst)
        assert(registry.specs[dep_inst].task.internal_state["blah"] == "bloo")

    def test_task_retrieval(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        name = spec.name
        registry.register_spec(spec)
        instance  = registry.instantiate_spec(name)
        result    = registry.make_task(instance)
        retrieved = registry.specs[result].task
        assert(isinstance(retrieved, Task_p))

    def test_task_get_default_status(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        name = spec.name
        registry.register_spec(spec)
        instance = registry.instantiate_spec(name)
        result   = registry.make_task(instance)
        status, _ = registry.get_status(result)
        assert(status is TaskStatus_e.INIT)

    def test_task_status_missing_task(self, registry):
        name = TaskName("basic::task")
        assert(registry.get_status(name) == (TaskStatus_e.NAMED, registry._tracker._declare_priority))

    def test_set_status(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        name = spec.name
        registry.register_spec(spec)
        instance = registry.instantiate_spec(name)
        result = registry.make_task(instance)
        assert(registry.get_status(result)[0] is TaskStatus_e.INIT)
        assert(registry.set_status(result, TaskStatus_e.SUCCESS) is True)
        assert(registry.get_status(result)[0] is TaskStatus_e.SUCCESS)

    def test_set_status_missing_task(self, registry):
        name = TaskName("basic::task")
        assert(registry.set_status(name, TaskStatus_e.SUCCESS) is False)

    def test_spec_retrieval(self, registry):
        spec = registry._tracker._factory.build({"name":"basic::task"})
        name = spec.name
        registry.register_spec(spec)
        retrieved = registry.specs[name].spec
        assert(retrieved == spec)
