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
from jgdv.structs.locator import Location
import doot

from doot.structs import DKey

logging = logmod.root

class TestLocation:

    def test_sanity(self):
        obj = Location("dir::>test/path")
        assert(obj is not None)

    def test_build(self):
        obj = Location("dir::>test/blah")
        assert(obj.path == pl.Path("test/blah"))

    def test_basic(self):
        obj = Location("dir::>test/blah")
        assert(obj is not None)

    def test_target(self):
        obj = Location("dir::>test/blah")
        assert(obj.path == pl.Path("test/blah"))

    def test_metadata(self):
        obj = Location("dir/protect::>test/blah")
        assert(Location.gmark_e.protect in obj)

    def test_metadata_opposite(self):
        obj = Location("dir::>test/blah")
        assert(Location.gmark_e.protect not in obj)

    def test_meta_in_path(self):
        obj = Location("file::>test/?.txt")
        assert(Location.bmark_e.select in obj.stem[0])

    def test_meta_in_path_glob(self):
        obj = Location("file::>test/*/blah.txt")
        assert(Location.gmark_e.abstract in obj)

    def test_meta_in_path_expansion(self):
        obj = Location("file::>test/{fname}.txt")
        assert(Location.gmark_e.abstract in obj)
        assert(Location.gmark_e.expand in obj)
