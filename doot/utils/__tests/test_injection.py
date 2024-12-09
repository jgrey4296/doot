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

doot._test_setup()
from doot import structs
from doot.task.base_job import DootJob
from doot.enums import TaskMeta_e
from doot.utils.injection import Injector_m
from doot._structs.relation_spec import RelationSpec

logging = logmod.root

class TestInjectorBuilding:

    @pytest.fixture(scope="function")
    def setup(self):
        self.inj   = Injector_m()

    def test_sanity(self, setup):
        assert(True)

    def test_empty_build_injection(self, setup):
        result = self.inj.build_injection({})
        assert(isinstance(result, dict))

    def test_base_format_fail(self, setup):
        with pytest.raises(doot.errors.DootStateError):
            self.inj.build_injection({"blah":[]})

    def test_basic_injection(self, setup):
        result = self.inj.build_injection({"now":["a"]})
        assert("a" in result)
        assert(result["a"] == "a")

    def test_injection_with_source(self, setup):
        result = self.inj.build_injection({"now":["a"]}, {"a": "{b}"})
        assert("a" in result)
        assert(result["a"] == "b")

    def test_injection_with_source_expansion(self, setup):
        result = self.inj.build_injection({"now":["a"]}, {"a": "{b}", "b": "c"})
        assert("a" in result)
        assert(result["a"] == "c")

    def test_injection_with_delayed_expanion(self, setup):
        result = self.inj.build_injection({"delay":["a"]}, {"a": "{b}", "b": "c"})
        assert("a" in result)
        assert(result["a"] == "{b}")

    def test_injection_with_insertion(self, setup):
        result = self.inj.build_injection({"insert": ["a"]}, insertion=25)
        assert("a" in result)
        assert(result["a"] == 25)

    def test_injection_with_constraint_fail(self, setup):
        with pytest.raises(doot.errors.DootStateError):
            self.inj.build_injection({"now": ["a"]}, {"a": "{b}", "b":"c"}, constraint={"d": 2})

    def test_injection_with_constraint_pass(self, setup):
        result = self.inj.build_injection({"now": ["a"]}, {"a": "{b}", "b":"c"}, constraint={"a": 2})
        assert("a" in result)
        assert(result["a"] == "c")
