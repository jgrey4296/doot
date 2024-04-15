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

class TestPathExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "bloo"}))

    @pytest.fixture(scope="function")
    def setup_locs(self, mocker):
        with doot.locs:
            doot.locs.update({"p1": "test1", "p2": "test2/sub"})
            yield

    @pytest.mark.parametrize("key,target,state", [("{x}", "blah", {"x": "blah"})])
    def test_to_path_basic(self, spec, mocker, setup_locs, key, target,state):
        obj = DootKey.build(key)
        result = obj.to_path(spec, state)
        assert(isinstance(result, pl.Path))
        assert(result.stem == target)

    def test_to_path_from_path(self, spec, mocker, setup_locs):
        result = DootKey.build(pl.Path("{x}"), strict=False).to_path(spec, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")

    def test_to_path_multi_path_expansion(self, spec, mocker, setup_locs):
        result = DootKey.build(pl.Path("{x}/{different}"), strict=False).to_path(spec, {"x": "blah", "different": "a/b/c"})
        assert(isinstance(result, pl.Path))
        rel = result.relative_to(pl.Path.cwd())
        assert(rel == pl.Path("blah/a/b/c"))

    def test_to_path_with_path_value(self, spec, mocker, setup_locs):
        result = DootKey.build(pl.Path("{x}/{different}"), strict=False).to_path(spec, {"x": "blah", "different": pl.Path("a/b/c")})
        assert(isinstance(result, pl.Path))
        rel = result.relative_to(pl.Path.cwd())
        assert(rel == pl.Path("blah/a/b/c"))

    def test_to_path_with_subexpansion(self, spec, mocker, setup_locs):
        result = DootKey.build(pl.Path("{x}/{different}"), strict=False).to_path(spec, {"x": "blah", "different": pl.Path("a/{x}/c")})
        assert(isinstance(result, pl.Path))
        rel = result.relative_to(pl.Path.cwd())
        assert(rel == pl.Path("blah/a/blah/c"))

    def test_to_path_loc_expansion(self, spec, mocker, setup_locs):
        result = DootKey.build("{p1}").to_path(spec, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "test1")

    def test_to_path_multi_expansion(self, spec, mocker, setup_locs):
        result = DootKey.build("{p1}/{x}", strict=False).to_path(spec, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")
        assert(result.parent.stem == "test1")

    def test_to_path_subdir(self, spec, mocker, setup_locs):
        result = DootKey.build("{p2}/{x}", strict=False).to_path(spec, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")
        assert(result.parent.stem == "sub")
        assert(result.parent.parent.stem == "test2")

    def test_missing_key_path(self, spec):
        key = DootKey.build("{q}", explicit=True)
        with pytest.raises(doot.errors.DootLocationError):
            key.to_path(spec, {"x": "blah"})

    def test_to_path_on_fail(self, spec):
        key = DootKey.build("{q}", explicit=True)
        result = key.to_path(spec, {"x": "blah"}, on_fail="qqqq")
        assert(isinstance(result, pl.Path))
        assert(result.name == "qqqq")

    def test_to_path_on_fail_existing_loc(self, spec, setup_locs):
        key = DootKey.build("{q}", explicit=True)
        result = key.to_path(spec, {"x": "blah"}, on_fail=DootKey.build("p2"))
        assert(isinstance(result, pl.Path))
        assert(result.parent.name == "test2")
        assert(result.name == "sub")

    def test_to_path_nop(self, spec):
        key = DootKey.build("{q}", explicit=True)
        result = key.to_path(spec, {"x": "blah"}, on_fail="blah")
        assert(result.name == "blah")

    def test_chain(self, spec):
        key = DootKey.build("{q}", explicit=True)
        result = key.to_path(spec, {"x": "blah"}, chain=[DootKey.build("t"), DootKey.build("x")])
        assert(isinstance(result, pl.Path))
        assert(result.name == "blah")

    def test_chain_nop(self, spec, setup_locs):
        key = DootKey.build("{p1}", explicit=True)
        result = key.to_path(spec, {"x": "blah"}, chain=[DootKey.build("t"), DootKey.build("x")])
        assert(isinstance(result, pl.Path))
        assert(result.name == "test1")

    def test_chain_into_on_fail(self, spec, setup_locs):
        key = DootKey.build("{nothing}", explicit=True)
        result = key.to_path(spec, {"x": "blah"}, chain=[DootKey.build("t"), DootKey.build("aweg")], on_fail=DootKey.build("p2"))
        assert(isinstance(result, pl.Path))
        assert(result.name == "sub")

    def test_expansion_extra(self, spec, setup_locs):
        key = DootKey.build("{p1}/blah/{y}/{aweg}", strict=False)
        assert(isinstance(key, DootKey))
        state = {"aweg": "doot"}
        result  = key.to_path(spec, state)
        assert(result == pl.Path("test1/blah/aweg/doot").expanduser().resolve())

    def test_expansion_with_ext(self, spec, setup_locs):
        key = DootKey.build("{y}.bib", strict=False)
        assert(isinstance(key, DootKey))
        state = {"aweg": "doot"}
        result  = key.to_path(spec, state)
        assert(result.name == "aweg.bib")

    @pytest.mark.xfail
    def test_expansion_redirect(self, spec, setup_locs):
        key = DootKey.build("aweg_", strict=False)
        assert(isinstance(key, DootKey))
        state = {"aweg": "p2"}
        result  = key.to_path(spec, state)
        assert(result == pl.Path("test2/sub").expanduser().resolve())

    @pytest.mark.parametrize("key,target,state", [("complex", "blah/jiojo/test1", {"x": "blah", "z": "aweg", "bloo": "jiojo", "complex": "{x}/{bloo}/{p1}" })])
    def test_path_expansion_rec(self, spec, setup_locs, key, target,  state):
        key_obj = DootKey.build(key)
        result = key_obj.to_path(spec, state)
        assert(result.relative_to(pl.Path.cwd()) == pl.Path(target))

    def test_cwd_expansion(self):
        key_obj = DootKey.build(".", explicit=True)
        result = key_obj.to_path(None, None)
        assert(result == pl.Path().resolve())
