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

import doot
from doot._structs.artifact import DootTaskArtifact

class TestTaskArtifact:

    @pytest.fixture(scope="function")
    def setup(self):
        pass

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass

    def test_initial(self):
        basic = DootTaskArtifact(pl.Path("a/b/c"))
        assert(basic is not None)

    def test_self_eq(self):
        basic = DootTaskArtifact(pl.Path("a/b/c"))
        assert(basic is basic)
        assert(basic == basic)


    def test_eq(self):
        basic = DootTaskArtifact(pl.Path("a/b/c"))
        basic2 = DootTaskArtifact(pl.Path("a/b/c"))
        assert(basic is not basic2)
        assert(basic == basic2)


    def test_neq(self):
        basic = DootTaskArtifact(pl.Path("a/b/c"))
        basic2 = DootTaskArtifact(pl.Path("a/b/d"))
        assert(basic is not basic2)
        assert(basic != basic2)


    def test_definite(self):
        basic = DootTaskArtifact(pl.Path("a/b/c"))
        assert(basic.is_definite)
        assert(basic._dstem)
        assert(basic._dsuffix)


    def test_indefinite_stem(self):
        basic = DootTaskArtifact(pl.Path("a/b/*.py"))
        assert(not basic.is_definite)
        assert(not basic._dstem)
        assert(basic._dsuffix)


    def test_indefinite_suffix(self):
        basic = DootTaskArtifact(pl.Path("a/b/c.*"))
        assert(not basic.is_definite)
        assert(basic._dstem)
        assert(not basic._dsuffix)


    def test_indefinite_path(self):
        basic = DootTaskArtifact(pl.Path("a/*/c.py"))
        assert(not basic.is_definite)
        assert(basic._dstem)
        assert(basic._dsuffix)


    def test_recursive_indefinite(self):
        basic = DootTaskArtifact(pl.Path("a/**/c.py"))
        assert(not basic.is_definite)
        assert(basic._dstem)
        assert(basic._dsuffix)


    def test_stem_contains(self):
        definite = DootTaskArtifact(pl.Path("a/b/c.py"))
        indef    = DootTaskArtifact(pl.Path("a/b/*.py"))
        assert(definite in indef)


    def test_not_contains_reverse(self):
        definite = DootTaskArtifact(pl.Path("a/b/c.py"))
        indef    = DootTaskArtifact(pl.Path("a/b/*.py"))
        assert(indef not in definite)


    def test_suffix_contains(self):
        definite = DootTaskArtifact(pl.Path("a/b/c.py"))
        indef    = DootTaskArtifact(pl.Path("a/b/c.*"))
        assert(definite in indef)


    def test_suffix_contain_fail(self):
        definite = DootTaskArtifact(pl.Path("a/b/d.py"))
        indef    = DootTaskArtifact(pl.Path("a/b/c.*"))
        assert(definite not in indef)


    def test_path_contains(self):
        definite = DootTaskArtifact(pl.Path("a/b/c.py"))
        indef    = DootTaskArtifact(pl.Path("a/*/c.py"))
        assert(definite in indef)


    def test_path_contain_fail(self):
        definite = DootTaskArtifact(pl.Path("b/b/c.py"))
        indef    = DootTaskArtifact(pl.Path("a/*/c.py"))
        assert(definite not in indef)


    def test_path_recursive_contains(self):
        definite = DootTaskArtifact(pl.Path("a/b/c.py"))
        indef    = DootTaskArtifact(pl.Path("a/**/c.py"))
        assert(definite in indef)


    def test_path_recursive_contain_fail(self):
        definite = DootTaskArtifact(pl.Path("b/b/c.py"))
        indef    = DootTaskArtifact(pl.Path("a/**/c.py"))
        assert(definite not in indef)


    def test_multi_depth_recursive_contains(self):
        definite = DootTaskArtifact(pl.Path("a/b/d/e/f/c.py"))
        indef    = DootTaskArtifact(pl.Path("a/**/c.py"))
        assert(definite in indef)


    def test_root_recursive_contains(self):
        definite = DootTaskArtifact(pl.Path("a/b/d/e/f/c.py"))
        indef    = DootTaskArtifact(pl.Path("**/c.py"))
        assert(definite in indef)


    def test_multi_indef_component_contains(self):
        definite = DootTaskArtifact(pl.Path("a/b/d/e/f/c.py"))
        indef    = DootTaskArtifact(pl.Path("**/*.*"))
        assert(definite in indef)
