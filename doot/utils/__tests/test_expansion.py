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

from tomlguard import TomlGuard
import doot
from doot.control.locations import DootLocations
import doot.utils.expansion
import doot.utils.expansion as exp

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

class TestExpansion:

    @pytest.fixture(scope="function")
    def setup_locs(self, mocker):
        new_locs = TomlGuard({"p1": "test1", "p2": "test2/sub"})
        return mocker.patch.object(exp.doot.locs, "_data", new_locs)


    @pytest.fixture(scope="function")
    def cleanup(self):
        pass

    def test_basic_to_str(self):
        result = exp.to_str("{x}", None, {"x": "blah"})
        assert(result == "blah")


    def test_bib_str(self):
        result = exp.to_str("{x}", None, {"x": " title        = {Architectonisches Alphabet, bestehend aus drey{\ss}ig Rissen },"})
        assert(result == " title        = {Architectonisches Alphabet, bestehend aus drey{\ss}ig Rissen },")


    def test_bib_str_simple(self):
        result = exp.to_str("{x}", None, {"x": r"\ss"})
        assert(result == "\ss")


    def test_multi_to_str(self):
        result = exp.to_str("{x}:{y}:{x}", None, {"x": "blah", "y":"bloo"})
        assert(result == "blah:bloo:blah")


    def test_to_str_fail(self):
        with pytest.raises(TypeError):
            exp.to_str("{x}", None, {"x": ["blah"]})


    def test_to_path_basic(self, mocker, setup_locs):
        result = exp.to_path("{x}", None, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")


    def test_to_path_loc_expansion(self, mocker, setup_locs):
        result = exp.to_path("{p1}", None, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "test1")


    def test_to_path_multi_expansion(self, mocker, setup_locs):
        result = exp.to_path("{p1}/{x}", None, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")
        assert(result.parent.stem == "test1")


    def test_to_path_subdir(self, mocker, setup_locs):
        result = exp.to_path("{p2}/{x}", None, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")
        assert(result.parent.stem == "sub")
        assert(result.parent.parent.stem == "test2")


    def test_to_any_basic(self, mocker, setup_locs):
        result = exp.to_any("{x}", None, {"x": set([1,2,3])})
        assert(isinstance(result, set))


    def test_to_any_multikey_fail(self, mocker, setup_locs):
        with pytest.raises(TypeError):
            result = exp.to_any("{x}{x}", None, {"x": set([1,2,3])})
