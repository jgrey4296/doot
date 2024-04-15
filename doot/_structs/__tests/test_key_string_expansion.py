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

class TestStringExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "bloo"}))

    @pytest.fixture(scope="function")
    def setup_locs(self, mocker):
        with doot.locs:
            doot.locs.update({"p1": "test1", "p2": "test2/sub"})
            yield

    def test_basic_to_str(self, spec):
        result = DootKey.build("{x}").expand(spec, {"x": "blah"})
        assert(result == "blah")

    def test_key_with_hyphen(self, spec):
        result = DootKey.build("{bloo-x}").expand(spec, {"bloo-x": "blah"})
        assert(result == "blah")

    def test_missing_key(self, spec):
        result = DootKey.build("{q}").expand(spec, {"x": "blah"})
        assert(result == "{q}")

    def test_basic_spec_pre_expand(self, spec):
        """
          z isnt a key, but z_ is, so that is used as the key,
          z_ == bloo, but bloo isn't a key, so {bloo} is returned
        """
        result = DootKey.build("z").expand(spec, {"x": "blah"})
        assert(result == "{bloo}")

    @pytest.mark.parametrize("key,target,state", [
        ("z", "jiojo", {"x": "blah", "z": "aweg", "bloo": "jiojo"}),
        ("x", "blah", {"x": "blah", "z": "aweg", "bloo": "jiojo"}),
        ("something", "{something}", {"x": "blah", "z": "aweg", "bloo": "jiojo"}),
        ("z", "jiojo", {"x": "blah", "z": "aweg", "bloo": "jiojo", "something_": "qqqq"}),
                             ])
    def test_prefer_explicit_key_to_default(self, spec, setup_locs, key, target, state):
        result = DootKey.build(key).expand(spec, state)
        assert(result == target)

    def test_pre_expand_wrap(self, spec):
        result = DootKey.build("z").expand(spec, {"x": "blah"})
        assert(result == "{bloo}")

    def test_wrap(self, spec):
        result = DootKey.build("y").expand(spec, {"x": "blah"})
        assert(result == "aweg")

    def test_actual_indirect_with_spec(self, spec):
        result = DootKey.build("y").expand(spec, {"x": "blah", "y_": "aweg"})
        assert(result == "aweg")

    @pytest.mark.filterwarnings("ignore:.*invalid escape sequence:DeprecationWarning")
    def test_bib_str(self, spec):
        result = DootKey.build("{x}").expand(spec, {"x": r" title        = {Architectonisches Alphabet, bestehend aus drey{\ss}ig Rissen },"})
        assert(result == r" title        = {Architectonisches Alphabet, bestehend aus drey{\ss}ig Rissen },")

    @pytest.mark.filterwarnings("ignore:.*invalid escape sequence:DeprecationWarning")
    def test_bib_str_simple(self, spec):
        result = DootKey.build("{x}").expand(spec, {"x": r"\ss"})
        assert(result == r"\ss")

    def test_multi_to_str(self, spec):
        result = DootKey.build("{x}:{y}:{x}", strict=False).expand(spec, {"x": "blah", "y":"bloo"})
        assert(result == "blah:aweg:blah")

    def test_path_as_str(self, spec, setup_locs):
        key = DootKey.build("{p2}/{x}")
        result = key.expand(spec, {"x": "blah", "y":"bloo"}, locs=doot.locs)
        assert(result.endswith("test2/sub/blah"))

    def test_expansion_to_false(self, spec, setup_locs):
        key = DootKey.build("{aFalse}")
        result = key.expand(spec, {"aFalse": False})
        assert(result == "False")

    @pytest.mark.xfail
    def test_to_str_fail(self, spec):
        with pytest.raises(TypeError):
            DootKey.build("{x}").expand(spec, {"x": ["blah"]})
