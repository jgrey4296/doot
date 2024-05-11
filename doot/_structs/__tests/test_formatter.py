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
import doot
doot._test_setup()

from doot.structs import ActionSpec
from doot._structs.key import DootFormatter

class TestDootFormatter:

    @pytest.fixture(scope="function")
    def setup_locs(self, mocker):
        new_locs = TomlGuard({"p1": "test1", "p2": "test2/sub"})
        return mocker.patch.object(doot.locs, "_data", new_locs)

    def test_initial(self, mocker):
        fmt = DootFormatter()
        spec = mocker.Mock(params={"a":"blah"}, spec=ActionSpec)
        result = fmt.format("{a}", _spec=spec, _state={})
        assert(result == "blah")

    def test_missing(self, mocker):
        fmt = DootFormatter()
        spec = mocker.Mock(params={"a":"blah"}, spec=ActionSpec)
        result = fmt.format("{b}", _spec=spec, _state={})
        assert(result == "{b}")


    def test_multi(self, mocker):
        fmt = DootFormatter()
        spec = mocker.Mock(params={"a":"blah"}, spec=ActionSpec)
        state = {"b": "aweg"}
        result = fmt.format("{a}:{b}", _spec=spec, _state=state)
        assert(result == "blah:aweg")


    def test_indirect(self, mocker):
        fmt = DootFormatter()
        spec = mocker.Mock(params={"a":"blah"}, spec=ActionSpec)
        state = {"b": "aweg"}
        result = fmt.format("{a}", _spec=spec, _state=state)
        assert(result == "blah")


    def test_recursive(self, mocker):
        fmt = DootFormatter()
        spec = mocker.Mock(params={"a":"this is a {b}"}, spec=ActionSpec)
        state = {"b": "aweg {c}", "c": "blah"}
        result = fmt.format("{a}", _spec=spec, _state=state, _rec=True)
        assert(result == "this is a aweg blah")


    def test_recursive_missing(self, mocker):
        fmt = DootFormatter()
        spec = mocker.Mock(params={"a":"this is a {b}"}, spec=ActionSpec)
        state = {"b": "aweg {c}", "c": "blah {d}"}
        result = fmt.format("{a}", _spec=spec, _state=state, _rec=True)
        assert(result == "this is a aweg blah {d}")


    @pytest.mark.xfail
    def test_not_str_fails(self, mocker):
        fmt = DootFormatter()
        spec = mocker.Mock(params={"a":"this is a {b}"}, spec=ActionSpec)
        state = {"b": "aweg {c}", "c": [1,2,3]}
        with pytest.raises(TypeError):
            fmt.format("{a}", _spec=spec, _state=state, _rec=True)


    def test_empty_format(self):
        fmt = DootFormatter()
        result = fmt.format(".")
        assert(result == ".")
