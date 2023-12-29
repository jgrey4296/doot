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

##-- pytest reminder
# caplog
# mocker.patch | patch.object | patch.multiple | patch.dict | stopall | stop | spy | stub
# pytest.mark.filterwarnings
# pytest.parameterize
# pytest.skip | skipif | xfail
# with pytest.deprecated_call
# with pytest.raises
# with pytest.warns(warntype)

##-- end pytest reminder

from tomlguard import TomlGuard
from doot.structs import DootActionSpec
from doot.utils.expansion import to_str, to_any

class TestStringExpand:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"y": "aweg", "test": "blah", "other": "bloo"}))


    def test_initial(self, spec):
        assert(to_str("test", spec, {}) == "blah")

    def test_state_simple(self, spec):
        assert("blah" == to_str("{test}", spec, {"test" : "blah"}))

    def test_state_multi(self, spec):
        assert("blah then blah" == to_str("{test} then {test}", spec, {"test" : "blah"}))

    def test_state_multi_different(self, spec):
        assert("blah then bloo" == to_str("{test} then {other}", spec, {"test" : "blah", "other":"bloo"}))

    def test_kwargs_simple(self, spec, mocker):
        assert("blah" == to_str("{test}", spec, {}))

    def test_kwargs_multi(self, spec, mocker):
        assert("blah then blah" == to_str("{test} then {test}", spec, {}))

    def test_kwargs_multi_diff(self, spec, mocker):
        assert("blah then bloo" == to_str("{test} then {other}", spec, {}))

    def test_kwargs_and_state_mixed(self, spec, mocker):
        state = {"state": "blee"}
        assert("blah then blee" == to_str("{test} then {state}", spec, state))

    def test_prefer_state_over_kwargs(self, spec, mocker):
        state = {"other": "blee"}
        assert("blah then blee" == to_str("{test} then {other}", spec, state))

    def test_expand_list_fails(self, spec, mocker):
        state = {"other": "bloo"}
        with pytest.raises(TypeError):
            to_str(["{test} then {other}"], spec, state)

    def test_expand_set_fails(self, spec, mocker):
        state = {"other": "bloo"}
        with pytest.raises(TypeError):
            to_str(set(["{test} then {other}"]), spec, state)

    def test_non_recursive(self, spec, mocker):
        state = {"other": "bloo", "rec": "{other}"}
        result = to_str("{rec}", spec, state)
        assert("{other}" == result)
        assert("bloo" == to_str(result, spec, state))


    def test_recursive(self, spec, mocker):
        state = {"other": "bloo", "rec": "{other}"}
        result = to_str("{rec}", spec, state, rec=True)
        assert("bloo" == result)

    @pytest.mark.xfail
    def test_list_replacement_failes(self, spec, mocker):
        state = {"other": "bloo", "test": ["a", "b", "c"]}
        with pytest.raises(TypeError):
            to_str("{test}", spec, state)

    def test_no_expansion_interference(self, spec, mocker):
        state = {"other": "short", "long": "looooooooooooooong"}
        result = to_str("{long}{other}", spec, state)
        assert("looooooooooooooongshort" == result)

    @pytest.mark.xfail
    def test_expand_non_str_value_fails(self, spec, mocker):
        state = {"other": "short", "adict": {"val" : "test"}}
        with pytest.raises(TypeError):
            to_str("{adict}", spec, state)
