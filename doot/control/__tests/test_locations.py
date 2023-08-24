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

import tomler
from doot.errors import DootDirAbsent, DootLocationExpansionError
from doot.control.locations import DootLocations

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

class TestLocations:

    def test_initial(self):
        simple = DootLocations(pl.Path.cwd())
        assert(isinstance(simple, DootLocations))
        assert(not bool(simple._data))

    def test_empty_repr(self):
        simple = DootLocations(pl.Path.cwd())
        repr_str = repr(simple)
        assert(repr_str == f"<DootLocations : {str(pl.Path.cwd())} : ()>")

    def test_non_empty_repr(self):
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah", "b": "aweg", "awegewag": "wejgio"})
        repr_str = repr(simple)
        assert(repr_str == f"<DootLocations : {str(pl.Path.cwd())} : (a, b, awegewag)>")

    def test_add_data(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))
        assert("a" in simple)

    def test_access_success(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))

        assert(simple.a == pl.Path("blah").absolute())
        assert(isinstance(simple.a, pl.Path))


    def test_access_expansion(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "{other}/blah", "other": "bloo"})
        assert(bool(simple._data))

        assert(simple.a == pl.Path("bloo/blah").absolute())
        assert(isinstance(simple.a, pl.Path))


    def test_access_nested_expansion(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "{other}/blah", "other": "{aweg}/bloo/{awog}", "aweg": "first", "awog": "second"})
        assert(bool(simple._data))

        assert(simple.a == pl.Path("first/bloo/second/blah").absolute())
        assert(isinstance(simple.a, pl.Path))


    def test_access_expansion_overload(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "{other}/blah", "other": "/bloo/{a}"})

        with pytest.raises(DootLocationExpansionError):
            simple.a

    def test_access_fail(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))

        with pytest.raises(tomler.TomlAccessError):
            simple.b

    def test_ensure_succeed(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))
        simple.ensure("a")

    def test_ensure_fail(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))

        with pytest.raises(DootDirAbsent):
            simple.ensure("b")

    def test_expand_tilde(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "~/blah"})
        assert(bool(simple._data))
        assert(simple.a.is_absolute())
        assert(simple.a == pl.Path("~/blah").expanduser())

    def test_expand_absolute(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "/blah"})
        assert(bool(simple._data))
        assert(simple.a.is_absolute())
        assert(simple.a == pl.Path("/blah"))

    def test_expand_relative(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))
        assert(simple.a.is_absolute())
        assert(simple.a == (pl.Path.cwd() / "blah").absolute())

    def test_expand_relative_with_different_cwd(self):
        simple = DootLocations(pl.Path("~/desktop/"))
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))
        assert(simple.a.is_absolute())
        assert(simple.a == (pl.Path("~/desktop/") / "blah").expanduser().absolute())

    def test_actual(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))

        assert(simple.get("a", "bloo") == pl.Path("blah").absolute())

    def test_get_default(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))

        assert(simple.get("b", "bloo") == pl.Path("bloo").absolute())

    def test_get_returns_path(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))

        assert(isinstance(simple.get("b", "bloo"), pl.Path))

    def test_context_manager(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))

        with simple(pl.Path("~/desktop")) as ctx:
            assert(ctx.a == (pl.Path("~/desktop/") / "blah").expanduser().absolute())