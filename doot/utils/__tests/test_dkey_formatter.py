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

from doot.structs import ActionSpec
from doot.utils.dkey_formatter import DKeyFormatter
from doot._structs.dkey import DKey
from doot._structs import dkey

class TestKeyFormatter:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do":"log", "args":[1,2,3], "val":"bloo", "a":"blah"})

    @pytest.fixture(scope="function")
    def setup_locs(self, mocker):
        new_locs = TomlGuard({"p1": "test1", "p2": "test2/sub"})
        return mocker.patch.object(doot.locs, "_data", new_locs)

    def test_parsing(self):
        val = "{bob}"
        result = DKeyFormatter.Parse(val)
        assert(bool(result))
        assert(val == "{bob}")

    def test_initial(self, mocker, spec):
        fmt           = DKeyFormatter()
        assert(isinstance(fmt, DKeyFormatter))
        assert(isinstance(spec, ActionSpec))
        assert(spec.kwargs.val == "bloo")
        assert(spec.kwargs.a == "blah")

    @pytest.mark.xfail
    def test_multi(self, mocker, spec):
        fmt           = DKeyFormatter()
        state         = {"b": "aweg"}
        result        = fmt.format("{a}:{b}", _spec=spec, _state=state)
        assert(result == "blah:aweg")

    @pytest.mark.xfail
    def test_recursive(self, mocker, spec):
        fmt = DKeyFormatter()
        state = {"b": "aweg {c}", "c": "blah"}
        result = fmt.format("{a}", _spec=spec, _state=state, _rec=True)
        assert(result == "this is a aweg blah")

    @pytest.mark.xfail
    def test_recursive_missing(self, mocker, spec):
        fmt = DKeyFormatter()
        state = {"b": "aweg {c}", "c": "blah {d}"}
        result = fmt.format("{a}", _spec=spec, _state=state, _rec=True)
        assert(result == "this is a aweg blah {d}")

    @pytest.mark.xfail
    def test_not_str_fails(self, mocker, spec):
        fmt = DKeyFormatter()
        state = {"b": "aweg {c}", "c": [1,2,3]}
        with pytest.raises(TypeError):
            fmt.format("{a}", _spec=spec, _state=state, _rec=True)
