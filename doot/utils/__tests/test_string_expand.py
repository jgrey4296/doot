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

from doot.structs import DootActionSpec
from doot.utils.expansion import to_str, to_any

class TestStringExpand:

    @pytest.fixture(scope="function")
    def setup(self):
        pass

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass

    def test_initial(self):
        assert("test" == to_str("test", None, None))

    def test_state_simple(self):
        assert("blah" == to_str("{test}", None, {"test" : "blah"}))

    def test_state_multi(self):
        assert("blah then blah" == to_str("{test} then {test}", None, {"test" : "blah"}))

    def test_state_multi_different(self):
        assert("blah then bloo" == to_str("{test} then {other}", None, {"test" : "blah", "other":"bloo"}))

    def test_kwargs_simple(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah"}
        assert("blah" == to_str("{test}", mock_spec, None))

    def test_kwargs_multi(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah"}
        assert("blah then blah" == to_str("{test} then {test}", mock_spec, None))

    def test_kwargs_multi_diff(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah", "other": "bloo"}
        assert("blah then bloo" == to_str("{test} then {other}", mock_spec, None))

    def test_kwargs_and_state_mixed(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah"}
        state = {"other": "bloo"}
        assert("blah then bloo" == to_str("{test} then {other}", mock_spec, state))

    def test_prefer_state_over_kwargs(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah", "other": "aweg"}
        state = {"other": "bloo"}
        assert("blah then bloo" == to_str("{test} then {other}", mock_spec, state))

    @pytest.mark.skip('TODO')
    def test_expand_list(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah", "other": "aweg"}
        state = {"other": "bloo"}
        assert(["blah then bloo"] == to_str(["{test} then {other}"], mock_spec, state))

    @pytest.mark.skip('TODO')
    def test_expand_set(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah", "other": "aweg"}
        state = {"other": "bloo"}
        assert(set(["blah then bloo"]) == to_str(set(["{test} then {other}"]), mock_spec, state))

    @pytest.mark.skip("TODO")
    def test_non_recursive(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "{other}", "other": "aweg"}
        state = {"other": "bloo"}
        result = to_str("{test}", mock_spec, state)
        assert("{other}" == result)
        assert("bloo" == to_str(result, mock_spec, state))

    @pytest.mark.skip('TODO')
    def test_flatten_list(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": ["a", "b", "c"]}
        state = {"other": "bloo"}
        result = to_str("{test}", mock_spec, state)
        assert("a b c" == result)

    def test_no_expansion_interference(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "looooooooooooooong"}
        state = {"other": "short"}
        result = to_str("{test}{other}", mock_spec, state)
        assert("looooooooooooooongshort" == result)

    @pytest.mark.skip('TODO')
    def test_expand_non_str_value(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": {"val" : "test"}}
        state = {"other": "short"}
        result = to_str("{test}", mock_spec, state)
        assert(result == str({"val": "test"}))
