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

import tomlguard
import doot
doot._test_setup()
from doot.errors import DootDirAbsent, DootLocationExpansionError, DootLocationError
from doot.control.locations import DootLocations
from doot.structs import DKey
from doot._structs.dkey import NonDKey

logging = logmod.root

class TestLocations:

    def test_initial(self):
        simple = DootLocations(pl.Path.cwd())
        assert(isinstance(simple, DootLocations))
        assert(not bool(simple._data))

    def test_update(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"blah": "bloo"})
        assert(bool(simple._data))
        assert("blah" in simple)

    @pytest.mark.skip
    def test_update_conflict(self):
        simple = DootLocations(pl.Path.cwd())
        simple.update({"blah": "bloo"})

        with pytest.raises(DootLocationError):
            simple.update({"blah": "blah"})

    def test_empty_repr(self):
        simple = DootLocations(pl.Path.cwd())
        repr_str = repr(simple)
        assert(repr_str == f"<DootLocations : {str(pl.Path.cwd())} : ()>")

    def test_non_empty_repr(self):
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah", "b": "aweg", "awegewag": "wejgio"})
        repr_str = repr(simple)
        assert(repr_str == f"<DootLocations : {str(pl.Path.cwd())} : (a, b, awegewag)>")

class TestLocationsBasicGet:

    def test_get_none(self):
        """
          loc.get(None) -> None
        """
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah"})
        result = simple.get(None)
        assert(result is None)

    def test_get_nonkey(self):
        """
          loc.get(NonDKey(simple)) -> pl.Path(.../simple)
        """
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah"})
        key = DKey("simple", explicit=True)
        assert(isinstance(key, NonDKey))
        result = simple.get(key)
        assert(result == pl.Path("simple"))

    def test_get_str(self):
        """
          loc.get('simple') -> pl.Path(.../simple)
        """
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah"})
        key = "simple"
        result = simple.get(key)
        assert(result == pl.Path("simple"))

    def test_get_str_key_no_expansion(self):
        """
          loc.get('{simple}') -> pl.Path(.../{simple})
        """
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah", "simple":"bloo"})
        key = "{simple}"
        result = simple.get(key)
        assert(result == pl.Path("{simple}"))

    def test_get_key_direct_expansion(self):
        """
          loc.get(DKey('simple')) => pl.Path(...bloo)
        """
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah", "simple":"bloo"})
        key = DKey("simple")
        result = simple.get(key)
        assert(result == pl.Path("bloo"))

    def test_get_missing(self):
        """
          loc.get(DKey('simple')) => pl.Path(...{simple})
        """
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah"})
        key = DKey("simple")
        result = simple.get(key)
        assert(result == pl.Path("{simple}"))

    def test_get_fallback(self):
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah"})
        assert(simple.get("{b}", pl.Path("bloo")) == pl.Path("bloo"))

    def test_get_raise_error_with_false_fallback(self):
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah"})
        with pytest.raises(DootLocationError):
            simple.get("badkey", False)

class TestLocationsGetItem:

    def test_getitem_str_no_expansion(self):
        """
          loc[a] => pl.Path(.../a)
        """
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah"})
        result = simple.__getitem__("a")
        result_alt = simple['a']
        assert(result == result_alt)
        assert(isinstance(result, pl.Path))
        assert(result == doot.locs.normalize(pl.Path("a")))

    def test_getitem_str_key_expansion(self):
        """
          loc[{a}] -> pl.Path(.../blah)
        """
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah"})
        result = simple.__getitem__("{a}")
        assert(result == doot.locs.normalize(pl.Path("blah")))

    def test_getitem_str_key_no_match_errors(self):
        """
          loc[{b}] -> pl.Path(.../{b})
        """
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah"})
        with pytest.raises(DootLocationError):
            simple.__getitem__("{b}")

    def test_getitem_path_passthrough(self):
        """
          loc[pl.Path(a/b/c)] -> pl.Path(.../a/b/c)
        """
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah"})
        result = simple.__getitem__(pl.Path("a/b/c"))
        assert(result == doot.locs.normalize(pl.Path("a/b/c")))

    def test_getitem_path_with_keys(self):
        """
          loc[pl.Path({a}/b/c)] -> pl.Path(.../blah/b/c)
        """
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah"})
        result = simple.__getitem__(pl.Path("{a}/b/c"))
        assert(result == doot.locs.normalize(pl.Path("blah/b/c")))

    def test_getitem_fail_with_multikey(self):
        simple = DootLocations(pl.Path.cwd()).update({"a": "{other}/blah", "other": "bloo"})
        key = DKey("{a}", ctor=pl.Path)
        with pytest.raises(TypeError):
            simple[key]

    def test_getitem_expansion_item(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "{other}", "other": "bloo"})
        assert(bool(simple._data))

        assert(isinstance(simple['{a}'], pl.Path))
        assert(simple['{a}'] == doot.locs.normalize(pl.Path("bloo")))


    def test_getitem_expansion_multi_recursive(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "{other}", "other": "{aweg}/bloo", "aweg":"aweg/{blah}", "blah":"blah/jojo"})
        assert(bool(simple._data))

        assert(isinstance(simple['{a}'], pl.Path))
        assert(simple['{a}'] == doot.locs.normalize(pl.Path("aweg/blah/jojo/bloo")))

    def test_getitem_expansion_in_item(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"other": "bloo"})
        assert(bool(simple._data))

        assert(isinstance(simple['{other}'], pl.Path))
        assert(simple['{other}'] == doot.locs.normalize(pl.Path("bloo")))

class TestLlocationsGetAttr:

    def test_attr_access_success(self):
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah"})
        result = simple.a
        assert(simple.a == pl.Path("blah").absolute())
        assert(isinstance(simple.a, pl.Path))

    def test_attr_access_simple_expansion(self):
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "{other}/blah", "other": "bloo"})
        assert(simple.a == simple.normalize(pl.Path("{other}/blah")))
        assert(isinstance(simple.a, pl.Path))

    def test_attr_expansion_simple(self):
        """
          locs.a => pl.Path(.../{other})
        """
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "{other}", "other": "bloo"})

        assert(isinstance(simple.a, pl.Path))
        assert(simple.a == pl.Path("{other}").absolute())

    def test_attr_access_non_existing_path(self):
        simple = DootLocations(pl.Path.cwd())
        simple.update({"a": "blah"})
        with pytest.raises(DootLocationError):
            simple.b

class TestLocationsFails:

    @pytest.mark.xfail
    def test_getitem_expansion_failure(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"other": "bloo"})
        assert(bool(simple._data))

        with pytest.raises(DootLocationError):
            simple['{aweg}']

    @pytest.mark.xfail
    def test_attr_access_nested_expansion(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "{other}/blah", "other": "{aweg}/bloo/{awog}", "aweg": "first", "awog": "second"})
        assert(bool(simple._data))

        assert(simple.a == pl.Path("first/bloo/second/blah").absolute())
        assert(isinstance(simple.a, pl.Path))

    @pytest.mark.xfail
    def test_attr_access_expansion_overload(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "{other}/blah", "other": "/bloo/{a}"})

        with pytest.raises(DootLocationExpansionError):
            simple.a

    @pytest.mark.xfail
    def test_get_returns_path(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))

        assert(isinstance(simple.get("b", pl.Path("bloo")), pl.Path))

class TestLocationsUtils:

    def test_normalize(self):
        simple = DootLocations(pl.Path.cwd())
        a_path = pl.Path("a/b/c")
        expected = a_path.absolute()
        result = simple.normalize(a_path)
        assert(result == expected)

    def test_normalize_tilde(self):
        simple = DootLocations(pl.Path.cwd())
        result = simple.normalize(pl.Path("~/blah"))
        assert(result.is_absolute())
        assert(result == pl.Path("~/blah").expanduser())

    def test_normalize_absolute(self):
        simple = DootLocations(pl.Path.cwd())
        result = simple.normalize(pl.Path("/blah"))
        assert(result.is_absolute())
        assert(result == pl.Path("/blah"))

    def test_normalize_relative(self):
        simple = DootLocations(pl.Path.cwd())
        result = simple.normalize(pl.Path("blah"))
        assert(result.is_absolute())
        assert(result == (pl.Path.cwd() / "blah").absolute())

    def test_normalize_relative_with_different_cwd(self):
        simple = DootLocations(pl.Path("~/desktop/"))
        result = simple.normalize(pl.Path("blah"))
        assert(result.is_absolute())
        assert(result == (pl.Path("~/desktop/") / "blah").expanduser().absolute())

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

    def test_context_manager(self):
        simple = DootLocations(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))

        with simple(pl.Path("~/Desktop")) as ctx:
            assert(ctx.a == (pl.Path("~/Desktop/") / "blah").expanduser().absolute())
