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

logging = logmod.root

import doot
doot._test_setup()
import doot.errors
from doot._structs.relation_spec import RelationSpec
from doot._structs.location import Location
from doot.structs import TaskName
from doot.enums import LocationMeta_f, RelationMeta_e

class TestRelationSpec:

    def test_initial(self):
        obj = RelationSpec.build("group::a.test")
        assert(isinstance(obj, RelationSpec))


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
        inject = { "a" : "b", "c": "d" }
        obj = RelationSpec.build({"task":"group::a.test", "inject": inject})
        assert(isinstance(obj, RelationSpec))
        assert(obj.inject == {"a": "b", "c": "d"})


    def test_injections_independent(self):
        inject = { "a" : "b", "c": "d" }
        obj = RelationSpec.build({"task":"group::a.test", "inject": inject})
        assert(isinstance(obj, RelationSpec))
        assert(obj.inject == {"a": "b", "c": "d"})
        inject['e'] = 5
        assert(obj.inject == {"a": "b", "c": "d"})

    def test_location_dep(self):
        obj = RelationSpec.build(pl.Path("a/file.txt"))
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))

    def test_file_dep(self):
        obj = RelationSpec.build("file:>a/file.txt")
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))
        assert(LocationMeta_f.file in obj.target)

    def test_abstract_file_dep(self):
        obj = RelationSpec.build("file:>a/?.txt")
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))
        assert(LocationMeta_f.file in obj.target)
        assert(LocationMeta_f.abstract in obj.target)

    def test_dict_loc_dep(self):
        obj = RelationSpec.build({"loc": "a/file.txt"})
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))

    def test_abstract_loc_dep_(self):
        obj = RelationSpec.build({"loc": "a/*.txt"})
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))
        assert(LocationMeta_f.abstract in obj.target)


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
        obj = RelationSpec.build({"task": "agroup::atask"}, relation=RelationMeta_e.dependsOn)
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, TaskName))
        assert(obj.relation is RelationMeta_e.dep)


    def test_build_as_requirement(self):
        obj = RelationSpec.build({"task": "agroup::atask"}, relation=RelationMeta_e.requirementFor)
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, TaskName))
        assert(obj.target == "agroup::atask")
        assert(obj.relation is RelationMeta_e.req)


    def test_invert(self):
        obj = RelationSpec.build({"task": "agroup::atask"})
        assert(obj.relation == RelationMeta_e.dependencyOf)
        inverted = obj.invert()
        assert(obj is not inverted)
        assert(obj.relation == RelationMeta_e.dependencyOf)
        assert(inverted.target == obj.target)
        assert(inverted.relation is not obj.relation)
