#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN202, B011
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
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

from jgdv.structs.locator import Location
import doot
import doot.errors
from doot.control.tracker.factory import TaskFactory
from ..._interface import RelationMeta_e
from .. import TaskName, InjectSpec, RelationSpec, TaskSpec

logging = logmod.root
factory = TaskFactory()

class TestRelationSpec:

    def test_initial(self):
        obj = RelationSpec.build("group::a.test")
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, TaskName))

    def test_constraint_list_build(self):
        obj = RelationSpec.build({"task":"group::a.test", "constraints": ["a" ,"b", "c"]})
        assert(isinstance(obj, RelationSpec))
        assert(obj.constraints == {"a":"a", "b":"b", "c":"c"})

    def test_constraint_dict_build(self):
        obj = RelationSpec.build({"task":"group::a.test", "constraints": {"a":"val", "b":"blah", "c":"other"}})
        assert(isinstance(obj, RelationSpec))
        assert(obj.constraints == {"a":"val", "b":"blah", "c":"other"})

    def test_constraints_independent(self):
        constraints = ["a", "b", "c"]
        obj = RelationSpec.build({"task":"group::a.test", "constraints": constraints})
        assert(isinstance(obj, RelationSpec))
        assert(obj.constraints == {"a":"a", "b":"b", "c":"c"})
        constraints.append("d")
        assert(obj.constraints == {"a":"a", "b":"b", "c":"c"})
        assert(id(obj.constraints) != id(constraints))

    def test_injections(self):
        inject = {"from_spec": { "a" : "{b}", "c": "{d}" }}
        obj = RelationSpec.build({"task":"group::a.test", "inject": inject})
        assert(isinstance(obj, RelationSpec))
        match obj.inject:
            case InjectSpec(from_spec=fs):
                assert(fs['a'] == "b")
            case x:
                 assert(False), x

    def test_injections_independent(self):
        inject = {"from_spec": { "a" : "{b}", "c": "{d}" }}
        obj = RelationSpec.build({"task":"group::a.test", "inject": inject})
        assert(isinstance(obj, RelationSpec))
        match obj.inject:
            case InjectSpec(from_spec=fs):
                inject['e'] = 5
                assert(fs == { "a" : "b", "c": "d" })
            case x:
                 assert(False), x

    def test_location_dep(self):
        obj = RelationSpec.build(pl.Path("a/file.txt"))
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))

    def test_file_dep(self):
        obj = RelationSpec.build("file::>a/file.txt")
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))
        assert(Location.Marks.file in obj.target)

    def test_abstract_file_dep(self):
        obj = RelationSpec.build("file::>a/?.txt")
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))
        assert(Location.Marks.file in obj.target)
        assert(Location.Marks.abstract in obj.target)

    def test_dict_loc_dep(self):
        obj = RelationSpec.build({"path": "file::>a/file.txt"})
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))

    def test_abstract_loc_dep_(self):
        obj = RelationSpec.build({"path": "a/*.txt"})
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))
        assert(Location.Marks.abstract in obj.target)

    def test_task_dep(self):
        obj = RelationSpec.build("agroup::atask")
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, TaskName))

    def test_dict_task(self):
        obj = RelationSpec.build({"task": "agroup::atask"})
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, TaskName))

    def test_dict_task_with_metadata(self):
        obj = RelationSpec.build({"task": "agroup::atask", "constraints":["a", "b", "c"]})
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, TaskName))
        assert(obj.constraints == {"a":"a", "b":"b", "c":"c"})

    def test_build_as_dependency(self):
        obj = RelationSpec.build({"task": "agroup::atask"}, relation=RelationMeta_e.needs)
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, TaskName))
        assert(obj.relation is RelationMeta_e.needs)

    def test_build_as_requirement(self):
        obj = RelationSpec.build({"task": "agroup::atask"}, relation=RelationMeta_e.blocks)
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, TaskName))
        assert(obj.target == "agroup::atask")
        assert(obj.relation is RelationMeta_e.blocks)

class TestRelationSpec_Acceptance:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_accepts_basic(self):
        obj           = RelationSpec.build({"task": "basic::target"})
        control_spec  = factory.build({"name":"basic::control"})
        control_i     = factory.instantiate(control_spec)
        target_spec   = factory.build({"name":"basic::target"})
        target_i      = factory.instantiate(target_spec)
        match obj.accepts(control_i, target_i):
            case True:
                assert(True)
            case x:
                 assert(False), x

    def test_accepts_fails_on_non_target(self):
        obj          = RelationSpec.build({"task": "basic::target"})
        control_spec = factory.build({"name":"basic::control"})
        control_i    = factory.instantiate(control_spec)
        target_spec  = factory.build({"name":"basic::not.target"})
        target_i     = factory.instantiate(target_spec)
        match obj.accepts(control_i, target_i):
            case False:
                assert(True)
            case x:
                 assert(False), x

    def test_accepts_fails_on_non_instance_target(self):
        obj          = RelationSpec.build({"task": "basic::target"})
        control_spec = factory.build({"name":"basic::control"})
        control_i    = factory.instantiate(control_spec)
        target_spec  = factory.build({"name":"basic::target"})
        match obj.accepts(control_i, target_spec):
            case False:
                assert(True)
            case x:
                 assert(False), x

    def test_accepts_fails_on_non_instance_control(self):
        obj          = RelationSpec.build({"task": "basic::target"})
        control_spec = factory.build({"name":"basic::control"})
        target_spec  = factory.build({"name":"basic::target"})
        target_i     = factory.instantiate(target_spec)
        match obj.accepts(control_spec, target_i):
            case False:
                assert(True)
            case x:
                 assert(False), x

    def test_accepts_with_constraints(self):
        """
        The relation accepts two specs when the constraint key matches
        """
        obj          = RelationSpec.build({"task": "basic::target",
                                           "constraints": ["blah"],
                                           })
        control_spec = factory.build({"name":"basic::control", "blah":"bloo"})
        target_spec  = factory.build({"name":"basic::target", "blah":"bloo"})
        control_i    = factory.instantiate(control_spec)
        target_i     = factory.instantiate(target_spec)
        match obj.accepts(control_i, target_i):
            case True:
                assert(True)
            case x:
                 assert(False), x

    def test_accepts_with_constraints_fail(self):
        """
        The relation doesnt accept two specs if the constraint key
        doesnt match
        """
        obj          = RelationSpec.build({"task": "basic::target",
                                           "constraints": ["blah"],
                                           })
        control_spec = factory.build({"name":"basic::control", "blah":"bloo"})
        target_spec  = factory.build({"name":"basic::target", "blah":"aweg"})
        control_i    = factory.instantiate(control_spec)
        target_i     = factory.instantiate(target_spec)
        match obj.accepts(control_i, target_i):
            case False:
                assert(True)
            case x:
                 assert(False), x

    def test_accepts_with_constraints_dict(self):
        """
        The relation accepts two specs
        if target[lhs_key] == control[rhs_key]

        so target.qqqq == control.blah
        *not* target.blah === control.qqqq
        """
        obj          = RelationSpec.build({"task": "basic::target",
                                           "constraints": {"qqqq": "blah"},
                                           })
        control_spec = factory.build({"name":"basic::control", "blah":"bloo"})
        target_spec  = factory.build({"name":"basic::target",
                                       "blah":"aweg",
                                       "qqqq":"bloo",
                                       })
        control_i    = factory.instantiate(control_spec)
        target_i     = factory.instantiate(target_spec)
        match obj.accepts(control_i, target_i):
            case True:
                assert(True)
            case x:
                 assert(False), x

    def test_accepts_with_contraints_dict_fail(self):
        """
        The relation fails to accept two specs
        if target[lhs_key] == control[rhs_key]

        so target.qqqq != control.blah
        """
        obj          = RelationSpec.build({"task": "basic::target",
                                           "constraints": {"qqqq": "blah"},
                                           })
        control_spec = factory.build({"name":"basic::control", "blah":"bloo"})
        target_spec  = factory.build({"name":"basic::target",
                                       "blah":"aweg",
                                       "qqqq":"blahaweg",
                                       })
        control_i    = factory.instantiate(control_spec)
        target_i     = factory.instantiate(target_spec)
        match obj.accepts(control_i, target_i):
            case False:
                assert(True)
            case x:
                 assert(False), x

    def test_accepts_with_control_missing_constraint_only(self):
        """
        The relation fails to accept two specs
        if target[lhs_key] == control[rhs_key]

        so target.qqqq != control.blah
        """
        obj          = RelationSpec.build({"task": "basic::target",
                                           "constraints": ["blah"],
                                           })
        control_spec = factory.build({"name":"basic::control"})
        target_spec  = factory.build({"name":"basic::target",
                                       "blah":"aweg",
                                       })
        control_i    = factory.instantiate(control_spec)
        target_i     = factory.instantiate(target_spec)
        match obj.accepts(control_i, target_i):
            case True:
                assert(True)
            case x:
                 assert(False), x


    def test_accepts_with_injection(self):
        """
        The relation fails to accept two specs
        if target[lhs_key] == control[rhs_key]

        so target.qqqq != control.blah
        """
        obj          = RelationSpec.build({"task": "basic::target",
                                           "inject": {"from_spec":["blah"]},
                                           })
        control_spec = factory.build({"name":"basic::control",
                                       "blah": "qqqq",
                                       })
        target_spec  = factory.build({"name":"basic::target",
                                       "blah":"qqqq",
                                       })
        control_i    = factory.instantiate(control_spec)
        target_i     = factory.instantiate(target_spec)
        match obj.accepts(control_i, target_i):
            case True:
                assert(True)
            case x:
                 assert(False), x
