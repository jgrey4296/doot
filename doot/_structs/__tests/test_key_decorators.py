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

class TestKeyDecorators:
    """ Test the key decorators """

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"x": "aweg", "y_": "a"}))

    @pytest.fixture(scope="function")
    def state(self):
        return {"a": "bloo", "b_": "blee", "c": "awegg"}

    def test_check_keys_basic_with_self(self):

        def an_action(self, spec, state):
            pass

        assert(dkey.DootKey.kwrap._check_keys(an_action, []))

    def test_check_keys_basic_no_self(self):

        def an_action(spec, state):
            pass

        assert(dkey.DootKey.kwrap._check_keys(an_action, []))

    def test_check_keys_fail_wrong_self(self):

        def an_action(notself, spec, state):
            pass

        assert(not dkey.DootKey.kwrap._check_keys(an_action, []))

    def test_check_keys_fail_no_self_wrong_spec(self):

        def an_action(notspec, state):
            pass

        assert(not dkey.DootKey.kwrap._check_keys(an_action, []))

    def test_check_keys_fail_no_self_wrong_state(self):

        def an_action(spec, notstate):
            pass

        assert(not dkey.DootKey.kwrap._check_keys(an_action, []))

    def test_check_keys_with_key(self):

        def an_action(spec, state, x):
            pass

        assert(dkey.DootKey.kwrap._check_keys(an_action, ["x"]))

    def test_check_keys_fail_with_wrong_key(self):

        def an_action(spec, state, x):
            pass

        assert(not dkey.DootKey.kwrap._check_keys(an_action, ["y"]))

    def test_check_keys_with_multi_keys(self):

        def an_action(spec, state, x, y):
            pass

        assert(dkey.DootKey.kwrap._check_keys(an_action, ["x", "y"]))

    def test_check_keys_fail_with_multi_keys(self):

        def an_action(spec, state, x, y):
            pass

        assert(not dkey.DootKey.kwrap._check_keys(an_action, ["x", "z"]))

    def test_check_keys_with_multi_keys_offset(self):

        def an_action(spec, state, x, y):
            pass

        assert(dkey.DootKey.kwrap._check_keys(an_action, ["y"], offset=1))

    def test_check_keys_fail_with_multi_keys_offset(self):

        def an_action(spec, state, x, y):
            pass

        assert(not dkey.DootKey.kwrap._check_keys(an_action, ["z"], offset=1))

    def test_basic_annotate(self):

        def an_action(spec, state, x, y):
            pass
        result = dkey.DootKey.kwrap._annotate_keys(an_action, ["x", "y"])
        assert(result)

    def test_basic_expand(self, spec, state):

        @dkey.DootKey.kwrap.expands("x")
        def an_action(spec, state, x):
            return x
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result == "aweg")

    def test_basic_method_expand(self, spec, state):

        @dkey.DootKey.kwrap.expands("x")
        def an_action(self, spec, state, x):
            return x
        assert(an_action.__name__ == "an_action")
        result = an_action(self, spec, state)
        assert(result == "aweg")

    def test_sequence_expand(self, spec, state):

        @dkey.DootKey.kwrap.expands("x")
        @dkey.DootKey.kwrap.expands("{c}/blah")
        def an_action(spec, state, x, y):
            return [x,y]
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result[0] == "aweg")
        assert(result[1] == "awegg/blah")

    def test_multi_expand(self, spec, state):

        @dkey.DootKey.kwrap.expands("x", "y")
        def an_action(spec, state, x, y):
            return [x,y]
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result[0] == "aweg")
        assert(result[1] == "bloo")

    def test_sequence_multi_expand(self, spec, state):

        @dkey.DootKey.kwrap.expands("x", "y")
        @dkey.DootKey.kwrap.expands("a", "c")
        def an_action(spec, state, x, y, a, c):
            return [x,y, a, c]
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result[0] == "aweg")
        assert(result[1] == "bloo")
        assert(result[2] == "bloo")
        assert(result[3] == "awegg")
