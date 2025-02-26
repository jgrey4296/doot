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
from doot._structs.artifact import TaskArtifact

class TestTaskArtifact:

    def test_initial(self):
        basic = TaskArtifact(pl.Path("a/b/c"))
        assert(basic is not None)

    def test_priority(self):
        basic = TaskArtifact(pl.Path("a/b/c"))
        assert(basic is not None)
        assert(basic.priority == 10)

    def test_priority_decrement(self):
        basic = TaskArtifact(pl.Path("a/b/c"))
        assert(basic is not None)
        assert(basic.priority == 10)
        basic.priority -= 1
        assert(basic.priority == 9)

    def test_self_eq(self):
        basic = TaskArtifact(pl.Path("a/b/c"))
        assert(basic is basic)
        assert(basic == basic)

    def test_eq(self):
        basic = TaskArtifact(pl.Path("a/b/c"))
        basic2 = TaskArtifact(pl.Path("a/b/c"))
        assert(basic is not None)
        assert(basic2 is not None)
        assert(basic is not basic2)
        assert(basic == basic2)

    def test_neq(self):
        basic  = TaskArtifact(pl.Path("a/b/c"))
        basic2 = TaskArtifact(pl.Path("a/b/d"))
        assert(basic is not basic2)
        assert(basic != basic2)

class TestArtifactReification:

    def test_reify_concrete(self):
        obj = TaskArtifact("test/blah.txt")
        target = pl.Path("test/blah.txt")
        with pytest.raises(NotImplementedError):
            obj.reify(target)

    def test_reify_path(self):
        obj    = TaskArtifact("test/*/blah.txt")
        target = pl.Path("test/other/blah.txt")
        match obj.reify(target):
            case None:
                assert(False)
            case TaskArtifact() as res:
                assert(res == "test/other/blah.txt")

    def test_reify_only_concrete_parts(self):
        obj    = TaskArtifact("test/*/blah.txt")
        target = pl.Path("*/other/blah.txt")
        match obj.reify(target):
            case None:
                assert(False)
            case TaskArtifact() as res:
                assert(res == "test/other/blah.txt")

    def test_reify_stem(self):
        obj                = TaskArtifact("test/?.txt")
        target             = pl.Path("test/blah.txt")
        result             = obj.reify(target)
        assert(result      == "test/blah.txt")

    def test_reify_only_stem(self):
        obj                = TaskArtifact("test/?.txt")
        target             = pl.Path("blah.txt")
        result             = obj.reify(target)
        assert(result      == "test/blah.txt")

    def test_reify_path_and_stem(self):
        obj           = TaskArtifact("*/?.txt")
        target        = pl.Path("test/blah.txt")
        result        = obj.reify(target)
        assert(result == "test/blah.txt")

    def test_reify_path_and_stem_fail(self):
        obj           = TaskArtifact("*/?.blah")
        target        = pl.Path("test/blah.txt")
        result        = obj.reify(target)
        assert(result is None)

    def test_reify_path_fail(self):
        obj    = TaskArtifact("other/?.txt")
        target = pl.Path("test/blah.txt")
        assert(obj.reify(target) is None)

    def test_reify_glob_path(self):
        obj           = TaskArtifact("*/blah.txt")
        target        = pl.Path("test/blah.txt")
        result        = obj.reify(target)
        assert(result == "test/blah.txt")

    def test_reify_rec_glob(self):
        obj           = TaskArtifact("test/**/blah.txt")
        target        = pl.Path("test/a/b/c/aweg")
        result        = obj.reify(target)
        assert(result == "test/a/b/c/aweg/blah.txt")

    def test_reify_suffix(self):
        obj           = TaskArtifact("other/blah.?")
        target        = pl.Path("blah.txt")
        result        = obj.reify(target)
        assert(result == "other/blah.txt")

    def test_reify_ext_with_path(self):
        obj           = TaskArtifact("other/blah.?")
        target        = pl.Path("other/blah.txt")
        result        = obj.reify(target)
        assert(result == "other/blah.txt")
