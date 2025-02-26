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

import doot
import doot.errors

from doot import structs
from doot.task.core.job import DootJob
from doot.enums import TaskMeta_e
from doot.mixins.matching import TaskMatcher_m
from doot._structs.relation_spec import RelationSpec

logging = logmod.root

class TestInjectorMatching:

    @pytest.fixture(scope="function")
    def setup(self):
        self.matcher = TaskMatcher_m()
        pass

    def test_sanity(self):
        assert(True is True)

    def test_match_pass(self, setup):
        target  = structs.TaskSpec.build({"name":"simple::test", "testval":"blah"})
        control = structs.TaskSpec.build({"name":"simple::test", "testval": "blah"})
        assert(self.matcher.match_with_constraints(target, control))

    def test_match_fail(self, setup):
        target  = structs.TaskSpec.build({"name":"simple::test", "testval":"blah"})
        control = structs.TaskSpec.build({"name":"simple::test", "testval":"bloo"})
        assert(not self.matcher.match_with_constraints(target, control))

    def test_match_name_fail(self, setup):
        target  = structs.TaskSpec.build({"name":"simple::other", "testval":"blah"})
        control = structs.TaskSpec.build({"name":"simple::test" , "testval": "blah"})
        assert(not self.matcher.match_with_constraints(target, control))

    def test_match_instance(self, setup):
        target  = structs.TaskSpec.build({"name":"simple::test"}).instantiate_onto(None)
        control = structs.TaskSpec.build({"name":"simple::test"})
        assert(self.matcher.match_with_constraints(target, control))

    def test_match_value(self, setup):
        target  = structs.TaskSpec.build({"name":"simple::test", "blah":5}).instantiate_onto(None)
        control = structs.TaskSpec.build({"name":"simple::test", "blah":5})
        assert(self.matcher.match_with_constraints(target, control))

    def test_match_value_multi(self, setup):
        target  = structs.TaskSpec.build({"name":"simple::test", "blah":5, "bloo": 10}).instantiate_onto(None)
        control = structs.TaskSpec.build({"name":"simple::test", "blah":5, "bloo": 10})
        assert(self.matcher.match_with_constraints(target, control))

    def test_match_value_fail_neq(self, setup):
        target = structs.TaskSpec.build({"name":"simple::test", "blah":10}).instantiate_onto(None)
        control = structs.TaskSpec.build({"name":"simple::test", "blah":4})
        assert(not self.matcher.match_with_constraints(target, control))

    def test_match_value_fail_missing(self, setup):
        target  = structs.TaskSpec.build({"name":"simple::test", "blah":5}).instantiate_onto(None)
        control = structs.TaskSpec.build({"name":"simple::test", "blah":5, "bloo": 10})
        assert(not self.matcher.match_with_constraints(target, control))

    def test_match_relation(self, setup):
        target  = structs.TaskSpec.build({"name":"simple::target", "blah":5}).instantiate_onto(None)
        control = structs.TaskSpec.build({"name":"simple::control", "blah":5})
        rel     = RelationSpec.build({"task":"simple::target"}, relation=RelationSpec.mark_e.needs)
        assert(self.matcher.match_with_constraints(target, control, relation=rel))

    def test_match_relation_fail(self, setup):
        target  = structs.TaskSpec.build({"name":"simple::target.sub", "blah":5}).instantiate_onto(None)
        control = structs.TaskSpec.build({"name":"simple::control", "blah":5})
        rel     = RelationSpec.build({"task":"simple::other"}, relation=RelationSpec.mark_e.needs)
        assert(not self.matcher.match_with_constraints(target, control, relation=rel))


    def test_match_relation_explicit_constraints(self, setup):
        target  = structs.TaskSpec.build({"name":"simple::target.sub", "blah":5}).instantiate_onto(None)
        control = structs.TaskSpec.build({"name":"simple::control", "blah":5})
        rel     = RelationSpec.build({"task":"simple::target", "constraints":{"blah":"blah"}}, relation=RelationSpec.mark_e.needs)
        assert(self.matcher.match_with_constraints(target, control, relation=rel))


    def test_match_relation_explicit_constraints_fail(self, setup):
        target  = structs.TaskSpec.build({"name":"simple::target.sub", "blah":5}).instantiate_onto(None)
        control = structs.TaskSpec.build({"name":"simple::control", "blah":5, "bloo": 10})
        rel     = RelationSpec.build({"task":"simple::target", "constraints":{"":"bloo"}}, relation=RelationSpec.mark_e.needs)
        assert(not self.matcher.match_with_constraints(target, control, relation=rel))
