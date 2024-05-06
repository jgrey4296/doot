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

import doot
doot._test_setup()
from doot._structs.artifact import DootTaskArtifact

class TestTaskArtifact:

    def test_initial(self):
        basic = DootTaskArtifact.build(pl.Path("a/b/c"))
        assert(basic is not None)

    def test_self_eq(self):
        basic = DootTaskArtifact.build(pl.Path("a/b/c"))
        assert(basic is basic)
        assert(basic == basic)

    def test_eq(self):
        basic = DootTaskArtifact.build(pl.Path("a/b/c"))
        basic2 = DootTaskArtifact.build(pl.Path("a/b/c"))
        assert(basic is not None)
        assert(basic2 is not None)
        assert(basic is not basic2)
        assert(basic == basic2)

    def test_neq(self):
        basic  = DootTaskArtifact.build(pl.Path("a/b/c"))
        basic2 = DootTaskArtifact.build(pl.Path("a/b/d"))
        assert(basic is not basic2)
        assert(basic != basic2)

    def test_definite_to_indefinite_contains(self):
        definite = DootTaskArtifact.build(pl.Path("a/b/c.py"))
        indef    = DootTaskArtifact.build(pl.Path("a/b/*.py"))
        assert(definite in indef)

class TestDefiniteArtifact:

    def test_definite(self):
        basic = DootTaskArtifact.build(pl.Path("a/b/c"))
        assert(basic.is_concrete)
        assert(basic.abstracts == (False, False, False))

class TestIndefiniteArtifact:

    def test_indefinite_stem(self):
        basic = DootTaskArtifact.build(pl.Path("a/b/*.py"))
        assert(not basic.is_concrete)
        assert(basic.abstracts == (False, True, False))

    def test_indefinite_suffix(self):
        basic = DootTaskArtifact.build(pl.Path("a/b/c.*"))
        assert(not basic.is_concrete)
        assert(basic.abstracts == (False, False, True))

    def test_indefinite_path(self):
        basic = DootTaskArtifact.build(pl.Path("a/*/c.py"))
        assert(not basic.is_concrete)
        assert(basic.abstracts == (True, False, False))

    def test_recursive_indefinite(self):
        basic = DootTaskArtifact.build(pl.Path("a/**/c.py"))
        assert(not basic.is_concrete)
        assert(basic.abstracts == (True, False, False))

    def test_indef_suffix_contains(self):

        definite = DootTaskArtifact.build(pl.Path("a/b/c.py"))
        indef    = DootTaskArtifact.build(pl.Path("a/b/c.*"))
        assert(definite in indef)

    def test_indef_suffix_contain_fail(self):

        definite = DootTaskArtifact.build(pl.Path("a/b/d.py"))
        indef    = DootTaskArtifact.build(pl.Path("a/b/c.*"))
        assert(definite not in indef)

    def test_indef_path_contains(self):

        definite = DootTaskArtifact.build(pl.Path("a/b/c.py"))
        indef    = DootTaskArtifact.build(pl.Path("a/*/c.py"))
        assert(definite in indef)

    def test_indef_path_contain_fail(self):

        definite = DootTaskArtifact.build(pl.Path("b/b/c.py"))
        indef    = DootTaskArtifact.build(pl.Path("a/*/c.py"))
        assert(definite not in indef)

    def test_indefinite_to_definite_contains_fail(self):

        definite = DootTaskArtifact.build(pl.Path("a/b/c.py"))
        indef    = DootTaskArtifact.build(pl.Path("a/b/*.py"))
        assert(indef not in definite)

    def test_indef_recursive_contains(self):

        definite = DootTaskArtifact.build(pl.Path("a/b/c.py"))
        indef    = DootTaskArtifact.build(pl.Path("a/**/c.py"))
        assert(definite in indef)

    def test_indef_recursive_contain_fail(self):

        definite = DootTaskArtifact.build(pl.Path("b/b/c.py"))
        indef    = DootTaskArtifact.build(pl.Path("a/**/c.py"))
        assert(definite not in indef)

    def test_indef_multi_recursive_contains(self):

        definite = DootTaskArtifact.build(pl.Path("a/b/d/e/f/c.py"))
        indef    = DootTaskArtifact.build(pl.Path("a/**/c.py"))
        assert(definite in indef)

    def test_indef_root_recursive_contains(self):

        definite = DootTaskArtifact.build(pl.Path("a/b/d/e/f/c.py"))
        indef    = DootTaskArtifact.build(pl.Path("**/c.py"))
        assert(definite in indef)

    def test_indef_multi_component_contains(self):

        definite = DootTaskArtifact.build(pl.Path("a/b/d/e/f/c.py"))
        indef    = DootTaskArtifact.build(pl.Path("**/*.*"))
        assert(definite in indef)

class TestArtifactMatching:

    def test_match_non_abstract(self):
        obj = DootTaskArtifact.build({"key":"test", "loc":"test/blah.txt"})
        target = pl.Path("test/blah.txt")
        result = obj.match_with(target)
        assert(result is None)

    def test_match_no_stem_wildcard(self):
        obj = DootTaskArtifact.build({"key":"test", "loc":"*/blah.txt"})
        target = pl.Path("test/blah.txt")
        result = obj.match_with(target)
        assert(result is None)

    def test_matching_stem(self):
        obj = DootTaskArtifact.build({"key":"test", "loc":"test/?.txt"})
        target = pl.Path("test/blah.txt")
        result = obj.match_with(target)
        assert(result.path == pl.Path("test/blah.txt"))

    def test_matching_path(self):
        obj = DootTaskArtifact.build({"key":"test", "loc":"*/?.blah"})
        target = pl.Path("test/blah.txt")
        result = obj.match_with(target)
        assert(result.path == pl.Path("test/blah.blah"))

    def test_matching_path_fail(self):
        obj = DootTaskArtifact.build({"key":"test", "loc":"other/?.blah"})
        target = pl.Path("test/blah.txt")
        result = obj.match_with(target)
        assert(result.path == pl.Path("other/blah.blah"))

    def test_glob_matching(self):
        obj = DootTaskArtifact.build({"key":"test", "loc":"*/?.blah"})
        target = pl.Path("test/blah.txt")
        result = obj.match_with(target)
        assert(result.path == pl.Path("test/blah.blah"))

    def test_rec_glob_matching(self):
        obj = DootTaskArtifact.build({"key":"test", "loc":"**/?.blah"})
        target = pl.Path("test/aweg/blah.txt")
        result = obj.match_with(target)
        assert(result.path == pl.Path("test/aweg/blah.blah"))

    def test_suffix_matching(self):
        obj = DootTaskArtifact.build({"key":"test", "loc":"other/?.?"})
        target = pl.Path("test/aweg/blah.txt")
        result = obj.match_with(target)
        assert(result.path == pl.Path("other/blah.txt"))
