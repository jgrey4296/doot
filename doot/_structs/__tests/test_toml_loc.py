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
doot._test_setup()

from doot._structs.toml_loc import TomlLocation

logging = logmod.root

class TestTomlLocation:

    @pytest.fixture(scope="function")
    def setup(self):
        pass

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass

    def test_initial(self):
        obj = TomlLocation.build("test", "test/path")
        assert(obj is not None)


    def test_basic(self):
        obj = TomlLocation.model_validate({"key":"test", "base":"test/blah"})
        assert(obj is not None)


    def test_copy(self):
        obj = TomlLocation.model_validate({"key":"test", "base":"test/blah"})
        obj2 = obj.model_copy()
        assert(obj is not obj2)


    def test_key(self):
        obj = TomlLocation.model_validate({"key":"test", "base":"test/blah"})
        assert(obj.key == "test")


    def test_base(self):
        obj = TomlLocation.model_validate({"key":"test", "base":"test/blah"})
        assert(obj.base == pl.Path("test/blah"))
