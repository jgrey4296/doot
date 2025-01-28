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
import types
import typing
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

# ##-- 1st party imports
import doot
import doot.errors

# ##-- end 1st party imports

doot._test_setup()
# ##-- 1st party imports
from doot import structs
from doot._structs.relation_spec import RelationSpec
from doot.enums import TaskMeta_e
from doot.mixins.injector import Injector_m, Injection_d
from doot.task.base_job import DootJob

# ##-- end 1st party imports

logging = logmod.root

@pytest.mark.xfail
class TestInjectionData:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic_build(self):
        assert(isinstance(Injection_d.build({}), Injection_d))

    def test_build_with_data(self):
        data = {"now":[], "delay":[], "insert":[]}
        match Injection_d.build(data):
            case Injection_d():
                assert(True)
            case x:
                assert(False), x

class TestInjector:

    @pytest.fixture(scope="function")
    def setup(self):
        self.inj   = Injector_m()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_empty_build_injection(self, setup):
        result = self.inj.build_injection({})
        assert(isinstance(result, dict))

    def test_now_injection(self, setup):
        """ Resulting dict has expansion to completion of 'now' injections """
        result = self.inj.build_injection({"now":["a"]},
                                          {"a": "{b}", "b": 5})
        assert("a" in result)
        assert(result["a"] == 5)

    def test_delay_injection(self, setup):
        """ Delayed injections have 1 expansion run on them """
        result = self.inj.build_injection({"delay":["a"]},
                                          {"a": "{b}", "b": 5}
                                          )
        assert("a" in result)
        assert(result["a"] == "{b}")

    def test_insert_injection(self, setup):
        """ insertion puts the insertion value into the named keys  """
        result = self.inj.build_injection({"insert":["a", "b"]},
                                          {"a": 5},
                                          insertion="blah"
                                          )
        assert("a" in result)
        assert(result["a"] == "blah")

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

    @pytest.mark.xfail
    def test_injection_with_constraint_fail(self, setup):
        with pytest.raises(doot.errors.StateError):
            self.inj.build_injection({"now": ["a"]}, {"a": "{b}", "b":"c"}, constraint={"d": 2})

    def test_injection_with_constraint_pass(self, setup):
        result = self.inj.build_injection({"now": ["a"]}, {"a": "{b}", "b":"c"}, constraint={"a": 2})
        assert("a" in result)
        assert(result["a"] == "c")

class TestInjectorParts:

    @pytest.fixture(scope="function")
    def setup(self):
        self.inj   = Injector_m()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_prep_keys_empty(self, setup):
        match Injection_d._prep_keys(None):
            case dict():
                assert(True)
            case x:
                assert(False), x

    def test_prep_keys_list(self, setup):
        match Injection_d._prep_keys(["a", "b","c"]):
            case {"a":"a", "b":"b", "c":"c"} as res:
                assert(all(isinstance(x, structs.DKey) for x in res.keys()))
                assert(True)
            case x:
                assert(False), x

    def test_prep_keys_dict(self, setup):
        match Injection_d._prep_keys({"a":"a", "b":"b", "c":"c"}):
            case {"a":"a", "b":"b", "c":"c"} as res:
                assert(all(isinstance(x, structs.DKey) for x in res.keys()))
                assert(all(isinstance(x, structs.DKey) for x in res.values()))
                assert(True)
            case x:
                assert(False), x
