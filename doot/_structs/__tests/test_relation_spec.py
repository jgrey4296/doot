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
from doot.enums import LocationMeta, RelationMeta

class TestRelationSpec:

    def test_initial(self):
        obj = RelationSpec.build("group::a.test")
        assert(isinstance(obj, RelationSpec))

    def test_location_dep(self):
        obj = RelationSpec.build(pl.Path("a/file.txt"))
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))

    def test_file_dep(self):
        obj = RelationSpec.build("file:>a/file.txt")
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))
        assert(LocationMeta.file in obj.target)

    def test_abstract_file_dep(self):
        obj = RelationSpec.build("file:>a/?.txt")
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))
        assert(LocationMeta.file in obj.target)
        assert(LocationMeta.abstract in obj.target)

    def test_dict_loc_dep(self):
        obj = RelationSpec.build({"loc": "a/file.txt"})
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))

    def test_abstract_loc_dep_(self):
        obj = RelationSpec.build({"loc": "a/*.txt"})
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, Location))
        assert(LocationMeta.abstract in obj.target)


    def test_task_dep(self):
        obj = RelationSpec.build("agroup::atask")
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, TaskName))


    def test_dict_task(self):
        obj = RelationSpec.build({"task": "agroup::atask"})
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, TaskName))


    def test_dict_task_with_metadata(self):
        obj = RelationSpec.build({"task": "agroup::atask", "keys":["a", "b", "c"]})
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, TaskName))
        assert(obj.constraints == ["a", "b", "c"])


    def test_build_as_dependency(self):
        obj = RelationSpec.build({"task": "agroup::atask"}, relation=RelationMeta.dependsOn)
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, TaskName))
        assert(obj.relation is RelationMeta.dep)


    def test_build_as_requirement(self):
        obj = RelationSpec.build({"task": "agroup::atask"}, relation=RelationMeta.requirementFor)
        assert(isinstance(obj, RelationSpec))
        assert(isinstance(obj.target, TaskName))
        assert(obj.relation is RelationMeta.req)
