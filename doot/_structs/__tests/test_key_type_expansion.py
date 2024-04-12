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

from tomlguard import TomlGuard
import doot
doot._test_setup()
from doot.control.locations import DootLocations
from doot.structs import DootKey, DootActionSpec
from doot._structs import key as dkey

KEY_BASES               : Final[str] = ["bob", "bill", "blah", "other"]
MULTI_KEYS              : Final[str] = ["{bob}/{bill}", "{blah}/{bloo}", "{blah}/{bloo}"]
NON_PATH_MUTI_KEYS      : Final[str] = ["{bob}_{bill}", "{blah} <> {bloo}", "! {blah}! {bloo}!"]
KEY_INDIRECTS           : Final[str] = ["bob_", "bill_", "blah_", "other_"]

TEST_LOCS               : Final[DootLocations] = DootLocations(pl.Path.cwd()).update({"blah": "doot"})

class TestTypeExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "bloo"}))

    @pytest.fixture(scope="function")
    def setup_locs(self, mocker):
        new_locs = TomlGuard({"p1": "test1", "p2": "test2/sub"})
        return mocker.patch.object(doot.locs, "_data", new_locs)

    def test_to_any_basic(self, spec, mocker, setup_locs):
        result = DootKey.build("{x}").to_type(spec, {"x": set([1,2,3])})
        assert(isinstance(result, set))

    def test_to_any_typecheck(self, spec, mocker, setup_locs):
        result = DootKey.build("{x}").to_type(spec, {"x": set([1,2,3])}, type_=set)
        assert(isinstance(result, set))

    def test_to_any_typecheck_union(self, spec, mocker, setup_locs):
        result = DootKey.build("{x}").to_type(spec, {"x": set([1,2,3])}, type_=set|list)
        assert(isinstance(result, set))

    def test_to_any_typecheck_union_2(self, spec, mocker, setup_locs):
        result = DootKey.build("x").to_type(spec, {"x": [1,2,3]}, type_=set|list)
        assert(isinstance(result, list))

    def test_to_any_missing_gives_none(self, spec, mocker, setup_locs):
        result = DootKey.build("z").to_type(spec, {}, type_=None)
        assert(result is None)

    def test_to_any_returns_none_or_str(self, spec, mocker, setup_locs):
        result = DootKey.build("z_").to_type(spec, {}, type_=str|None)
        assert(result is None)

    def test_to_any_typecheck_fail(self, spec, mocker, setup_locs):
        with pytest.raises(TypeError):
            DootKey.build("{x}").to_type(spec, {"x": set([1,2,3])}, type_=list)

    def test_to_any_multikey_fail(self, spec, mocker, setup_locs):
        with pytest.raises(TypeError):
            DootKey.build("{x}{x}", strict=False).to_type(spec, {"x": set([1,2,3])})

    def test_missing_key_any(self, spec):
        result = DootKey.build("{q}").to_type(spec, {"x": "blah"})
        assert(result == None)

    def test_missing_key_to_on_fail(self, spec):
        result = DootKey.build("{q}").to_type(spec, {"x": "blah"}, on_fail=2)
        assert(result == 2)

    def test_on_fail_nop(self, spec):
        result = DootKey.build("{x}").to_type(spec, {"x": "blah"}, on_fail=2)
        assert(result == "blah")

    def test_chain(self, spec):
        result = DootKey.build("{nothing}").to_type(spec, {"x": "blah"}, chain=[DootKey.build("also_no"), DootKey.build("x")])
        assert(result == "blah")

    def test_chain_into_on_fail(self, spec):
        result = DootKey.build("{nothing}").to_type(spec, {"x": "blah"}, chain=[DootKey.build("also_no"), DootKey.build("xawegw")], on_fail=2)
        assert(result == 2)
