#!/usr/bin/env python1
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
import decorator
import pytest
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot

# ##-- end 1st party imports

doot._test_setup()
# ##-- 1st party imports
from doot.control.locations import DootLocations
from doot.structs import ActionSpec, DootKey
from doot.utils.decorators import DecorationUtils as DecU
from doot.utils.decorators import DootDecorator as DDec
from doot.utils.key_decorator import Keyed

# ##-- end 1st party imports

logging = logmod.root
KEY_BASES               : Final[str] = ["bob", "bill", "blah", "other"]
MULTI_KEYS              : Final[str] = ["{bob}/{bill}", "{blah}/{bloo}", "{blah}/{bloo}"]
NON_PATH_MUTI_KEYS      : Final[str] = ["{bob}_{bill}", "{blah} <> {bloo}", "! {blah}! {bloo}!"]
KEY_INDIRECTS           : Final[str] = ["bob_", "bill_", "blah_", "other_"]

TEST_LOCS               : Final[DootLocations] = DootLocations(pl.Path.cwd()).update({"blah": "doot"})

class TestKeyDecoratorsCalls:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"x": "aweg", "y_": "a"}))

    @pytest.fixture(scope="function")
    def state(self):
        return {"a": "bloo", "b_": "blee", "c": "awegg"}

    def test_basic_annotate(self):

        def an_action(spec, state, x, y):
            pass
        result = DecU._update_key_annotations(an_action, ["x", "y"])
        assert(result)

    def test_basic_expand(self, spec, state):

        @Keyed.expands("x")
        def an_action(spec, state, x):
            return x
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result == "aweg")

    def test_expand_fail_with_nonmatching_paramname(self, spec, state):

        with pytest.raises(doot.errors.DootKeyError):
            @Keyed.expands("x")
            def an_action(spec, state, y):
                return x

    def test_expand_with_underscore_param(self, spec, state):

        @Keyed.expands("x")
        def an_action(spec, state, _y):
            return _y

        result = an_action(spec, state)
        assert(result == "aweg")

    def test_type_with_underscore_param(self, spec, state):
        state['from'] = "aweg"

        @Keyed.types("from")
        @Keyed.types("to")
        def an_action(self, spec, state, _from, to):
            return _from

        result = an_action(None, spec, state)
        assert(result == "aweg")

    def test_basic_method_expand(self, spec, state):

        @Keyed.expands("x")
        def an_action(self, spec, state, x):
            return x
        assert(an_action.__name__ == "an_action")
        result = an_action(self, spec, state)
        assert(result == "aweg")

    def test_sequence_expand(self, spec, state):

        @Keyed.expands("x")
        @Keyed.expands("{c}/blah")
        def an_action(spec, state, x, _y):
            return [x,_y]

        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result[0] == "aweg")
        assert(result[1] == "awegg/blah")


    def test_error_on_non_identifier(self, spec, state):

        with pytest.raises(doot.errors.DootKeyError):
            @Keyed.expands("{c}/blah")
            def an_action(spec, state, y):
                return y


    def test_multi_expand(self, spec, state):

        @Keyed.expands("x", "y")
        def an_action(spec, state, x, y):
            return [x,y]
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result[0] == "aweg")
        assert(result[1] == "bloo")

    def test_sequence_multi_expand(self, spec, state):

        @Keyed.expands("x", "y")
        @Keyed.expands("a", "c")
        def an_action(spec, state, x, y, a, c):
            return [x,y, a, c]
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result[0] == "aweg")
        assert(result[1] == "bloo")
        assert(result[2] == "bloo")
        assert(result[3] == "awegg")
