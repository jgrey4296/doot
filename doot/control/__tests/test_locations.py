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

import doot
from jgdv.structs.locator import JGDVLocator
from jgdv.structs.locator.errors import DirAbsent, LocationExpansionError, LocationError
from doot.util.dkey import DKey, NonDKey

logging = logmod.root

class TestLocations:

    def test_initial(self):
        simple = JGDVLocator(pl.Path.cwd())
        assert(isinstance(simple, JGDVLocator))
        assert(not bool(simple._data))

    def test_update(self):
        simple = JGDVLocator(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"blah": "bloo"})
        assert(bool(simple._data))
        assert("blah" in simple)

    def test_registered(self):
        simple = JGDVLocator(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))
        simple.registered("a")

    def test_registered_fail(self):
        simple = JGDVLocator(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))

        with pytest.raises(DirAbsent):
            simple.registered("b")

    def test_update_conflict(self):
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"blah": "bloo"})
        with pytest.raises(LocationError):
            simple.update({"blah": "blah"})

    def test_update_non_strict(self):
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"blah": "bloo"})
        simple.update({"blah": "bloo"}, strict=False)

    def test_update_overwrite(self):
        target = pl.Path("aweg")
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"blah": "bloo"})
        simple.update({"blah": "aweg"}, strict=False)
        assert("blah" in simple)
        assert(simple._data["blah"].path == target)
        assert(simple['{blah}'] == simple.normalize(target))

    def test_empty_repr(self):
        simple = JGDVLocator(pl.Path.cwd())
        repr_str = repr(simple)
        assert(repr_str == f"<JGDVLocator (1) : {str(pl.Path.cwd())} : ()>")

    def test_non_empty_repr(self):
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah", "b": "aweg", "awegewag": "wejgio"})
        repr_str = repr(simple)
        assert(repr_str == f"<JGDVLocator (1) : {str(pl.Path.cwd())} : (a, b, awegewag)>")

    def test_context_manager(self):
        simple = JGDVLocator(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))
        assert(simple.a.path == pl.Path("blah"))

        with simple(pl.Path("~/Desktop")) as ctx:
            assert(ctx["{a}"] == pl.Path("~/Desktop/blah").expanduser().resolve())

    def test_clear(self):
        simple = JGDVLocator(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert("a" in simple)
        simple.clear()
        assert("a" not in simple)

class TestLocationsBasicGet:

    def test_get_none(self):
        """
          loc.get(None) -> None
        """
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah"})
        with pytest.raises(KeyError):
            simple.get(None)

    def test_get_nonkey(self):
        """
          loc.get(NonDKey(simple)) -> pl.Path(.../simple)
        """
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah"})
        key = DKey("simple", implicit=False)
        assert(isinstance(key, NonDKey))
        result = simple[key]
        assert(result == simple.normalize(pl.Path("simple")))

    def test_get_str(self):
        """
          loc.get('simple') -> pl.Path(.../simple)
        """
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah"})
        key = "simple"
        result = simple[key]
        assert(result == simple.normalize(pl.Path("simple")))

    def test_get_key_no_expansion(self):
        """
          loc.get(DKey('simple')) => pl.Path(...bloo)
        """
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah", "simple":"bloo"})
        key = DKey("simple", implicit=True)
        result = simple.get(key)
        assert(result == pl.Path("bloo"))

    @pytest.mark.xfail
    def test_get_missing(self):
        """
          loc.get(DKey('simple')) => pl.Path(...{simple})
        """
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah"})
        key = DKey("simple", implicit=True)
        result = simple[key]
        assert(result == simple.normalize(pl.Path("{simple}")))

    def test_get_fallback(self):
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah"})
        result = simple.get("{b}", pl.Path("bloo"))
        assert(result == pl.Path("bloo"))

    def test_get_raise_error_with_no_fallbac(self):
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah"})
        with pytest.raises(KeyError):
            simple.get("{badkey}")

class TestLocationsGetItem:

    def test_getitem_str_no_expansion(self):
        """
          loc[a] => pl.Path(.../a)
        """
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah"})
        result = simple['a']
        assert(isinstance(result, pl.Path))
        assert(result == doot.locs.normalize(pl.Path("a")))

    def test_getitem_str_key_expansion(self):
        """
          loc[{a}] -> pl.Path(.../blah)
        """
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah"})
        result = simple["{a}"]
        assert(result == doot.locs.normalize(pl.Path("blah")))

    @pytest.mark.xfail
    def test_getitem_str_key_no_match_errors(self):
        """
          loc[{b}] -> pl.Path(.../{b})
        """
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah"})
        assert(simple["{b}"] == simple.norm(pl.Path("{b}")))

    def test_getitem_path_passthrough(self):
        """
          loc[pl.Path(a/b/c)] -> pl.Path(.../a/b/c)
        """
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah"})
        result = simple.__getitem__(pl.Path("a/b/c"))
        assert(result == doot.locs.normalize(pl.Path("a/b/c")))

    def test_getitem_path_with_keys(self):
        """
          loc[pl.Path({a}/b/c)] -> pl.Path(.../blah/b/c)
        """
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah"})
        result = simple.__getitem__(pl.Path("{a}/b/c"))
        assert(result == doot.locs.normalize(pl.Path("blah/b/c")))

    def test_getitem_multikey(self):
        simple             = JGDVLocator(pl.Path.cwd()).update({"a": "{other}/blah", "other": "bloo"})
        key                = DKey("{a}/{other}", ctor=pl.Path)
        target             = simple.norm(pl.Path("bloo/blah/bloo"))
        match simple[key]:
            case pl.Path() as x if x == target:
                assert(True)
            case x:
                assert(False), x

    def test_getitem_expansion_item(self):
        simple = JGDVLocator(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "{other}", "other": "bloo"})
        assert(bool(simple._data))

        assert(isinstance(simple['{a}'], pl.Path))
        assert(simple['{a}'] == doot.locs.normalize(pl.Path("bloo")))

    def test_getitem_expansion_multi_recursive(self):
        target = doot.locs.normalize(pl.Path("aweg/blah/jojo/bloo"))
        simple = JGDVLocator(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "{other}", "other": "{aweg}/bloo", "aweg":"aweg/{blah}", "blah":"blah/jojo"})
        assert(bool(simple._data))

        assert(isinstance(simple['{a}'], pl.Path))
        assert(simple['{a}'] == target)

    def test_getitem_expansion_in_item(self):
        simple = JGDVLocator(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"other": "bloo"})
        assert(bool(simple._data))

        assert(isinstance(simple['{other}'], pl.Path))
        assert(simple['{other}'] == doot.locs.normalize(pl.Path("bloo")))

class TestLlocationsGetAttr:

    def test_attr_access_success(self):
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah"})
        result = simple.a
        assert(simple.a.path == pl.Path("blah"))

    def test_attr_no_sub_expansion(self):
        """
          locs.a => pl.Path(.../{other})
        """
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "{other}", "other": "bloo"})

        assert(simple.a.path == pl.Path("{other}"))

    def test_attr_access_non_existing_path(self):
        simple = JGDVLocator(pl.Path.cwd())
        simple.update({"a": "blah"})
        with pytest.raises(AttributeError):
            simple.b

class TestLocationsFails:

    @pytest.mark.xfail
    def test_getitem_expansion_missing_key(self):
        simple = JGDVLocator(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"other": "bloo"})
        assert(bool(simple._data))
        assert(simple['{aweg}'] == simple.norm(pl.Path("{aweg}")))

    @pytest.mark.xfail
    def test_item_access_expansion_recursion_fail(self):
        simple = JGDVLocator(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "{other}/blah", "other": "/bloo/{a}"})
        with pytest.raises(RecursionError):
            simple['{a}']

    def test_get_returns_path(self):
        simple = JGDVLocator(pl.Path.cwd())
        assert(not bool(simple._data))
        simple.update({"a": "blah"})
        assert(bool(simple._data))
        assert(isinstance(simple.get("b", pl.Path("bloo")), pl.Path))

class TestLocationsUtils:

    def test_normalize(self):
        simple = JGDVLocator(pl.Path.cwd())
        a_path = pl.Path("a/b/c")
        expected = a_path.absolute()
        result = simple.normalize(a_path)
        assert(result == expected)

    def test_normalize_tilde(self):
        simple = JGDVLocator(pl.Path.cwd())
        result = simple.normalize(pl.Path("~/blah"))
        assert(result.is_absolute())
        assert(result == pl.Path("~/blah").expanduser())

    def test_normalize_absolute(self):
        simple = JGDVLocator(pl.Path.cwd())
        result = simple.normalize(pl.Path("/blah"))
        assert(result.is_absolute())
        assert(result == pl.Path("/blah"))

    def test_normalize_relative(self):
        simple = JGDVLocator(pl.Path.cwd())
        result = simple.normalize(pl.Path("blah"))
        assert(result.is_absolute())
        assert(result == (pl.Path.cwd() / "blah").absolute())

    def test_normalize_relative_with_different_cwd(self):
        simple = JGDVLocator(pl.Path("~/desktop/"))
        result = simple.normalize(pl.Path("blah"))
        assert(result.is_absolute())
        assert(result == (pl.Path("~/desktop/") / "blah").expanduser().absolute())
