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

from jgdv.structs.locator import Location
import doot
import doot.errors
from doot._structs.relation_spec import RelationSpec, RelationMeta_e
from doot.structs import TaskName

logging = logmod.root

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
        inject = {"now": { "a" : "b", "c": "d" }}
        obj = RelationSpec.build({"task":"group::a.test", "inject": inject})
        assert(isinstance(obj, RelationSpec))
        assert(obj.inject == {"now": {"a": "b", "c": "d"}})

    def test_injections_independent(self):
        inject = {"now": { "a" : "b", "c": "d" }}
        obj = RelationSpec.build({"task":"group::a.test", "inject": inject})
        assert(isinstance(obj, RelationSpec))
        assert(obj.inject == {"now": { "a" : "b", "c": "d" }})
        inject['e'] = 5
        assert(obj.inject == {"now": { "a" : "b", "c": "d" }})

    def test_location_dep(self):
        obj = RelationSpec.build(pl.Path("a/file.txt"))
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))

    def test_file_dep(self):
        obj = RelationSpec.build("file::>a/file.txt")
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))
        assert(Location.gmark_e.file in obj.target)

    def test_abstract_file_dep(self):
        obj = RelationSpec.build("file::>a/?.txt")
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))
        assert(Location.gmark_e.file in obj.target)
        assert(Location.gmark_e.abstract in obj.target)

    def test_dict_loc_dep(self):
        obj = RelationSpec.build({"path": "file::>a/file.txt"})
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))

    def test_abstract_loc_dep_(self):
        obj = RelationSpec.build({"path": "a/*.txt"})
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))
        assert(Location.gmark_e.abstract in obj.target)

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
