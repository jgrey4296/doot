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
from jgdv.structs.location import Location, LocationMeta_f
import doot
doot._test_setup()

from doot.structs import DKey
from doot.enums import LocationMeta_f

logging = logmod.root

class TestLocation:

    def test_sanity(self):
        obj = Location.build("test/path", key="test")
        assert(obj is not None)

    def test_build(self):
        obj = Location.build({"key":"test", "path":"test/blah"})
        assert(obj.path == pl.Path("test/blah"))

    def test_basic(self):
        obj = Location.build({"key":"test", "path":"test/blah"})
        assert(obj is not None)

    def test_copy(self):
        obj = Location.build({"key":"test", "path":"test/blah"})
        obj2 = obj.model_copy()
        assert(obj is not obj2)

    def test_key(self):
        obj = Location.build({"key":"test", "path":"test/blah"})
        assert(isinstance(obj.key, DKey))
        assert(obj.key == "test")

    def test_target(self):
        obj = Location.build({"key":"test", "path":"test/blah"})
        assert(obj.path == pl.Path("test/blah"))

    def test_metadata(self):
        obj = Location.build({"key":"test", "path":"test/blah", "protected":True})
        assert(obj.check(LocationMeta_f.protected))
        assert(LocationMeta_f.protected in obj)

    def test_metadata_opposite(self):
        obj = Location.build({"key":"test", "path":"test/blah", "protected":False})
        assert(LocationMeta_f.protected not in obj)

    def test_meta_in_path(self):
        obj = Location.build({"key":"test", "path":"test/?.txt"})
        assert(LocationMeta_f.abstract in obj)
        assert(LocationMeta_f.glob not in obj)
        assert(obj.abstracts == (False, True, False))

    def test_meta_in_path_glob(self):
        obj = Location.build({"key":"test", "path":"test/*/blah.txt"})
        assert(LocationMeta_f.abstract in obj)
        assert(LocationMeta_f.glob in obj)
        assert(obj.abstracts == (True, False, False))

    def test_meta_in_path_expansion(self):
        obj = Location.build({"key":"test", "path":"test/{fname}.txt"})
        assert(LocationMeta_f.abstract in obj)
        assert(LocationMeta_f.glob not in obj)
        assert(LocationMeta_f.expandable in obj)
        assert(bool(obj.keys()))
        assert("fname" in obj.keys())
        assert(obj.abstracts == (False, True, False))


    def test_normOnLoad(self):
        obj = Location.build({"key":"test", "path":"test/blah.txt", "normOnLoad": True})
        assert(obj.path.is_absolute())
        assert(obj.path.is_relative_to(pl.Path.cwd()))

    def test_userpath_normOnLoad(self):
        obj = Location.build({"key":"test", "path":"~/test/blah.txt", "normOnLoad": True})
        assert(obj.path.is_absolute())
        assert(obj.path.is_relative_to(pl.Path.home()))
