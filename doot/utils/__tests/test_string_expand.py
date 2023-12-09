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
from doot.utils.string_expand import expand_str, expand_set, expand_to_obj

class TestStringExpand:

    @pytest.fixture(scope="function")
    def setup(self):
        pass

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass

    def test_initial(self):
        assert("test" == expand_str("test", None, None))

    def test_state_simple(self):
        assert("blah" == expand_str("{test}", None, {"test" : "blah"}))

    def test_state_multi(self):
        assert("blah then blah" == expand_str("{test} then {test}", None, {"test" : "blah"}))

    def test_state_multi_different(self):
        assert("blah then bloo" == expand_str("{test} then {other}", None, {"test" : "blah", "other":"bloo"}))

    def test_kwargs_simple(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah"}
        assert("blah" == expand_str("{test}", mock_spec))

    def test_kwargs_multi(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah"}
        assert("blah then blah" == expand_str("{test} then {test}", mock_spec))


    def test_kwargs_multi_diff(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah", "other": "bloo"}
        assert("blah then bloo" == expand_str("{test} then {other}", mock_spec))


    def test_kwargs_and_state_mixed(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah"}
        state = {"other": "bloo"}
        assert("blah then bloo" == expand_str("{test} then {other}", mock_spec, state))


    def test_prefer_state_over_kwargs(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah", "other": "aweg"}
        state = {"other": "bloo"}
        assert("blah then bloo" == expand_str("{test} then {other}", mock_spec, state))


    def test_expand_list(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah", "other": "aweg"}
        state = {"other": "bloo"}
        assert(["blah then bloo"] == expand_str(["{test} then {other}"], mock_spec, state))


    def test_expand_set(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah", "other": "aweg"}
        state = {"other": "bloo"}
        assert(set(["blah then bloo"]) == expand_str(set(["{test} then {other}"]), mock_spec, state))


    @pytest.mark.skip("TODO")
    def test_non_recursive(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "{other}", "other": "aweg"}
        state = {"other": "bloo"}
        result = expand_str("{test}", mock_spec, state)
        assert("{other}" == result)
        assert("bloo" == expand_str(result, mock_spec, state))


    def test_flatten_list(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": ["a", "b", "c"]}
        state = {"other": "bloo"}
        result = expand_str("{test}", mock_spec, state)
        assert("a b c" == result)


    def test_no_expansion_interference(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "looooooooooooooong"}
        state = {"other": "short"}
        result = expand_str("{test}{other}", mock_spec, state)
        assert("looooooooooooooongshort" == result)


    def test_expand_non_str_value(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": {"val" : "test"}}
        state = {"other": "short"}
        result = expand_str("{test}", mock_spec, state)
        assert(result == str({"val": "test"}))


    def test_expand_as_key(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "other"}
        state = {"other": "short"}
        result = expand_str("{test}", mock_spec, state, as_key=True)
        assert(result == "{other}")
        expanded_result = expand_str(result, mock_spec, state)
        assert(expanded_result == "short")


    def test_expand_key_no_initial_replace(self, mocker):
        mock_spec = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "other"}
        state = {"other": "short"}
        result = expand_str("test", mock_spec, state, as_key=True)
        assert(result == "{test}")
        expanded_result = expand_str(result, mock_spec, state)
        assert(expanded_result == "other")


class TestSetExpand:

    def test_initial(self):
        assert(set(["test"]) == expand_set("test", None, None))


    def test_simple_expand(self, mocker):
        mock_spec        = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah"}
        state            = {"other": "bloo"}
        assert(set(["blah"])  == expand_set("{test}", mock_spec, state))


    def test_expand_input_list(self, mocker):
        mock_spec        = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": "blah"}
        state            = {"other": "bloo"}
        assert(set(["blah", "bloo"])  == expand_set(["{test}", "{test}", "{other}"], mock_spec, state))


    def test_expand_list(self, mocker):
        mock_spec        = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": ["a", "b", "c"]}
        state            = {"other": "bloo"}
        assert(set(["a", "b", "c"])  == expand_set("{test}", mock_spec, state))


    def test_non_recursive(self, mocker):
        mock_spec        = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": ["a", "{other}", "c"]}
        state            = {"other": "bloo"}
        assert(set(["a", "{other}", "c"])  == expand_set("{test}", mock_spec, state))


    def test_multi_list(self, mocker):
        mock_spec        = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": ["a", "{other}", "c"]}
        state            = {"blah": ["bloo", "aweg"]}
        result = expand_set("{test}{blah}", mock_spec, state)
        logging.debug("Result: %s", result)
        assert(set(["a", "{other}", "c", "bloo", "aweg"])  == result)


    def test_simple_no_key(self, mocker):
        mock_spec        = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": ["a", "{other}", "c"]}
        state            = {"blah": ["bloo", "aweg"]}
        result = expand_set("test", mock_spec, state)
        logging.debug("Result: %s", result)
        assert(set(["test"])  == result)


    def test_simple_no_key_repeat(self, mocker):
        mock_spec        = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": ["a", "{other}", "c"]}
        state            = {"blah": ["bloo", "aweg"]}
        result = expand_set("test", mock_spec, state)
        result = expand_set(result, mock_spec, state)
        logging.debug("Result: %s", result)
        assert(set(["test"])  == result)


    def test_expand_not_strs(self, mocker):
        mock_spec        = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": [1,2,3,4],}
        state            = {"blah": [2,3,6,7], }
        result = expand_set(["{test}", "{blah}"], mock_spec, state)
        logging.debug("Result: %s", result)
        assert(set([1,2,3,4,6,7])  == result)


class TestObjExpand:

    def test_initial(self):
        with pytest.raises(KeyError):
            expand_to_obj("test", None, None)


    def test_simple_expand(self, mocker):
        mock_spec        = mocker.MagicMock(spec=DootActionSpec)
        mock_spec.kwargs = {"test": set([1, 2, 3, 4, 5, 4])}
        state            = {"other": "bloo"}
        assert(set([1,2,3,4,5])  == expand_to_obj("{test}", mock_spec, state))


class TestKeyExpand:
    pass
