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
from doot.utils.string_expand import expand_str

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
