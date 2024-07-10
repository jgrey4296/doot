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
from doot._structs.dkey import DKey, MultiDKey
from doot._structs import dkey

@pytest.fixture(scope="function")
def spec():
    return ActionSpec.build({"do":"log", "args":[1,2,3], "val":"bloo", "a":"blah"})

@pytest.fixture(scope="function")
def setup_locs( mocker):
    new_locs = TomlGuard({"p1": "test1", "p2": "test2/sub"})
    return mocker.patch.object(doot.locs, "_data", new_locs)


class TestDKeyFormatter:

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


class TestDKeyFormatter_Expansion:

    @pytest.fixture(scope="function")
    def sources(self):
        return [
            { "a": "blah", "testrec": DKey("subrec")},
            { "b" : "bloo", "subrec": "aweg" },
            { "c_": "a" },
            { "complex": [1,2,3,4], "indcomplex_": "complex" },
            ]


    def test_initial(self, mocker, spec):
        fmt           = DKeyFormatter()
        assert(isinstance(fmt, DKeyFormatter))
        assert(isinstance(spec, ActionSpec))
        assert(spec.kwargs.val == "bloo")
        assert(spec.kwargs.a == "blah")


    def test_single_expansion(self, sources):
        fmt           = DKeyFormatter()
        with fmt(sources=sources) as ctx:
            result = ctx._single_expand(DKey("a"))

        assert(result == "blah")


    def test_single_expansion_to_complex_type(self, sources):
        fmt           = DKeyFormatter()
        with fmt(sources=sources) as ctx:
            result = ctx._single_expand(DKey("complex"))

        assert(result == [1,2,3,4])


    def test_indirect_expansion(self, sources):
        fmt           = DKeyFormatter()
        with fmt(sources=sources) as ctx:
            result = ctx._expand(DKey("c_"))

        assert(result == "blah")


    def test_indirect_expansion_to_complex_type(self, sources):
        fmt           = DKeyFormatter()
        with fmt(sources=sources) as ctx:
            result = ctx._expand(DKey("indcomplex_"))

        assert(result == [1,2,3,4])


    def test_redirection(self, sources):
        fmt           = DKeyFormatter()
        with fmt(sources=sources) as ctx:
            ctx.rec_remaining = 1
            result = ctx._try_redirection(DKey("c_"))

        assert(isinstance(result, list))
        assert(len(result) == 1)
        assert(result[0] == "a")


    def test_recursive_expansion(self, sources):
        fmt           = DKeyFormatter()
        with fmt(sources=sources) as ctx:
            result = ctx._expand(DKey("testrec"))

        assert(result == "aweg")


    def test_multikey_expansion(self, sources):
        fmt           = DKeyFormatter()
        key = DKey("blah :: {b} {b}")
        assert(isinstance(key, MultiDKey))
        with fmt(sources=sources) as ctx:
            result = ctx._multi_expand(key)

        assert(result == "blah :: bloo bloo")


    def test_multikey_multi_expansion(self, sources):
        fmt           = DKeyFormatter()
        key = DKey("blah :: {b} :: {a}")
        assert(isinstance(key, MultiDKey))
        assert(len(key.keys()) == 2)
        with fmt(sources=sources) as ctx:
            result = ctx._multi_expand(key)

        assert(result == "blah :: bloo :: blah")


    def test_multikey_recursive_expansion(self, sources):
        fmt           = DKeyFormatter()
        key = DKey("blah :: {testrec} {b}")
        assert(isinstance(key, MultiDKey))
        with fmt(sources=sources) as ctx:
            result = ctx._multi_expand(key)

        assert(result == "blah :: aweg bloo")


    @pytest.mark.xfail
    def test_multikey_failure_on_complex_type(self, sources):
        fmt           = DKeyFormatter()
        key = DKey("blah :: {complex}")
        assert(isinstance(key, MultiDKey))
        with pytest.raises(ValueError), fmt(sources=sources) as ctx:
            result = ctx._multi_expand(key)



    def test_str_expansion_recursive(self, sources):
        fmt           = DKeyFormatter()
        key = "blah :: {testrec}"
        assert(not isinstance(key, DKey))
        with fmt(sources=sources) as ctx:
            result = ctx._str_expand(key)

        assert(result == "blah :: aweg")


    def test_str_expansion(self, sources):
        fmt           = DKeyFormatter()
        key = "blah :: {a}"
        assert(not isinstance(key, DKey))
        with fmt(sources=sources) as ctx:
            result = ctx._str_expand(key)

        assert(result == "blah :: blah")



class TestDKeyFormatter_Formatting:

    def test_initial(self, mocker, spec):
        fmt           = DKeyFormatter()
        assert(isinstance(fmt, DKeyFormatter))
        assert(isinstance(spec, ActionSpec))
        assert(spec.kwargs.val == "bloo")
        assert(spec.kwargs.a == "blah")


    def test_simple_format(self, mocker, spec):
        fmt           = DKeyFormatter()
        result = fmt.format("test")
        assert(result == "test")


    def test_simple_key_replace(self, mocker, spec):
        fmt           = DKeyFormatter()
        result = fmt.format("{test}", test="aweg")
        assert(result == "aweg")


    def test_simple_key_wrap(self, mocker, spec):
        fmt           = DKeyFormatter()
        result = fmt.format("{test:w}", test="aweg")
        assert(result == "{aweg}")
