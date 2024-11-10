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

import tomlguard
import doot
import doot.errors

doot._test_setup()
from doot import structs
from doot.task.base_job import DootJob
from doot.enums import TaskMeta_f
from doot.utils.injection import Injector_m

logging = logmod.root

class TestInjector:

    @pytest.fixture(scope="function")
    def setup(self):
        self.inj = Injector_m()
        pass

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass

    def test_sanity(self):
        assert(True is True)

    def test_match_with_constraints_pass(self, setup):
        spec1 = structs.TaskSpec.build({"name":"simple::test"})
        spec2 = structs.TaskSpec.build({"name":"simple::test"})
        assert(self.inj.match_with_constraints(spec1, spec2))

    def test_match_with_constraints_instanced(self, setup):
        spec1 = structs.TaskSpec.build({"name":"simple::test"}).instantiate_onto(None)
        spec2 = structs.TaskSpec.build({"name":"simple::test"})
        assert(self.inj.match_with_constraints(spec1, spec2))

    def test_match_with_constraints_with_value(self, setup):
        spec1 = structs.TaskSpec.build({"name":"simple::test", "blah":5}).instantiate_onto(None)
        spec2 = structs.TaskSpec.build({"name":"simple::test", "blah":5})
        assert(self.inj.match_with_constraints(spec1, spec2))

    def test_match_with_constraints_with_value_fail(self, setup):
        spec1 = structs.TaskSpec.build({"name":"simple::test", "blah":10}).instantiate_onto(None)
        spec2 = structs.TaskSpec.build({"name":"simple::test", "blah":5})
        assert(not self.inj.match_with_constraints(spec1, spec2))

    def test_match_with_contraints_missing_value_from_control(self, setup):
        spec1 = structs.TaskSpec.build({"name":"simple::test", "blah":5}).instantiate_onto(None)
        spec2 = structs.TaskSpec.build({"name":"simple::test", "blah":5, "bloo": 10})
        assert(not self.inj.match_with_constraints(spec1, spec2))
