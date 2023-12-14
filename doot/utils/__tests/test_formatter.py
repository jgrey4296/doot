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
from doot.structs import DootActionSpec
import doot.utils.expansion as exp


class TestDootFormatter:

    @pytest.fixture(scope="function")
    def setup_locs(self, mocker):
        new_locs = TomlGuard({"p1": "test1", "p2": "test2/sub"})
        return mocker.patch.object(exp.doot.locs, "_data", new_locs)

    def test_initial(self):
        fmt = exp.DootFormatter()
        spec = DootActionSpec(kwargs={"a":"blah"})
        result = fmt.format("{a}", _spec=spec, _state={})
        assert(result == "blah")

    def test_missing(self):
        fmt = exp.DootFormatter()
        spec = DootActionSpec(kwargs={"a":"blah"})
        result = fmt.format("{b}", _spec=spec, _state={})
        assert(result == "{b}")


    def test_multi(self):
        fmt = exp.DootFormatter()
        spec = DootActionSpec(kwargs={"a":"blah"})
        state = {"b": "aweg"}
        result = fmt.format("{a}:{b}", _spec=spec, _state=state)
        assert(result == "blah:aweg")


    def test_indirect(self):
        fmt = exp.DootFormatter()
        spec = DootActionSpec(kwargs={"a":"blah"})
        state = {"b": "aweg"}
        result = fmt.format("{a}", _spec=spec, _state=state)
        assert(result == "blah")


    def test_recursive(self):
        fmt = exp.DootFormatter()
        spec = DootActionSpec(kwargs={"a":"this is a {b}"})
        state = {"b": "aweg {c}", "c": "blah"}
        result = fmt.format("{a}", _spec=spec, _state=state, _rec=True)
        assert(result == "this is a aweg blah")


    def test_recursive_missing(self):
        fmt = exp.DootFormatter()
        spec = DootActionSpec(kwargs={"a":"this is a {b}"})
        state = {"b": "aweg {c}", "c": "blah {d}"}
        result = fmt.format("{a}", _spec=spec, _state=state, _rec=True)
        assert(result == "this is a aweg blah {d}")


    def test_not_str_fails(self):
        fmt = exp.DootFormatter()
        spec = DootActionSpec(kwargs={"a":"this is a {b}"})
        state = {"b": "aweg {c}", "c": [1,2,3]}
        with pytest.raises(TypeError):
            fmt.format("{a}", _spec=spec, _state=state, _rec=True)


    def test_path_expansion(self, setup_locs):
        fmt = exp.DootFormatter()
        spec = DootActionSpec(kwargs={"a":"blah"})
        result = fmt.format("{p1}/{a}", _spec=spec, _state={}, _as_path=True)
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")
        assert(result.parent.stem == "test1")
