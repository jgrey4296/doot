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

logging = logmod.root

import doot
doot._test_setup()
from doot.actions.job_injection import JobInjector
import doot.errors
from doot.structs import DootKey, DootActionSpec, DootTaskName

class TestJobInjection:
    """

    """

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec.from_data({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": DootTaskName.from_str("basic")}

    def test_copy(self, spec, state):
        """ the injection copies the value over directly """
        state.update({"a": 2})
        inj = JobInjector()
        injection = inj.build_injection(spec, state, dict(copy=["a"]))
        assert("a" in injection)
        assert(injection['a'] == 2)

    def test_copy_multikey(self, spec, state):
        """ the injection doesn't expand a multikey """
        state.update({"a": "{x} : {y}", "x": 5, "y": 10})
        inj = JobInjector()
        injection = inj.build_injection(spec, state, dict(copy=["a"]))
        assert("a" in injection)
        assert(injection['a'] == "{x} : {y}")

    def test_expand(self, spec, state):
        """ the injection expands the key to its value, adding it under the original key """
        spec.kwargs._table().update({"a_": "b"})
        state.update({"b": 5})
        inj = JobInjector()
        injection = inj.build_injection(spec, state, dict(expand=["a"]))
        assert("a" in injection)
        assert(injection['a'] == 5)

    def test_copy_doesnt_expand(self, spec, state):
        """ a copied indirect key will copy its redirected value """
        spec.kwargs._table().update({"a_": "b"})
        state.update({"b": 5})
        inj = JobInjector()
        injection = inj.build_injection(spec, state, dict(copy=["a_"]))
        assert("a" in injection)
        assert("a_" not in injection)
        assert(injection['a'] == 5)

    def test_copy_remap(self, spec, state):
        """ copied values can be remapped to new key names """
        state.update({"a": 2})
        inj = JobInjector()
        injection = inj.build_injection(spec, state, dict(copy={"test":"a"}))
        assert("test" in injection)
        assert("a" not in injection)
        assert(injection['test'] == 2)

    def test_expand_remap(self, spec, state):
        """ expanded injections can be remapped to new key names """
        state.update({"a": 2})
        inj = JobInjector()
        injection = inj.build_injection(spec, state, dict(expand={"test":"a"}))
        assert("test" in injection)
        assert("a" not in injection)
        assert(injection['test'] == 2)

    def test_replacement(self, spec, state):
        """ keys can be inserted with the defined replacement value """
        state.update({"a": 2})
        inj = JobInjector()
        injection = inj.build_injection(spec, state, dict(replace=["a"]), replacement=10)
        assert("a" in injection)
        assert(injection['a'] == 10)


class TestPathInjection:

    def test_initial(self):
        pass

    def test_inject_shadow(self):
        pass

class TestNameInjection:

    def test_initial(self):
        pass

class TestActionInjection:

    def test_initial(self):
        pass
