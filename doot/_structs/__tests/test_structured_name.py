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
# doot._test_setup()
from doot._structs.structured_name import StructuredName

class TestStructuredName:

    @pytest.fixture(scope="function")
    def setup(self):
        pass

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass

    def test_initial(self):
        obj = StructuredName.build("head::tail")
        assert(isinstance(obj, StructuredName))

    def test_build_fail(self):
        with pytest.raises(ValueError):
            StructuredName.build("head:tail")

    def test_head_str(self):
        obj = StructuredName.build("head.a.b.c::tail")
        assert(obj.head == ["head", "a", "b", "c"])
        assert(obj.head_str() == "head.a.b.c")

    def test_tail_str(self):
        obj = StructuredName.build("head::tail.a.b.c")
        assert(obj.tail == ["tail", "a", "b", "c"])
        assert(obj.tail_str() == "tail.a.b.c")


    def test_hash(self):
        obj = StructuredName.build("head::tail.a.b.c")
        obj2 = StructuredName.build("head::tail.a.b.c")
        assert(hash(obj) == hash(obj2))


    def test_lt(self):
        obj = StructuredName.build("head::tail.a.b.c")
        obj2 = StructuredName.build("head::tail.a.b.c.d")
        assert( obj < obj2 )


    def test_not_lt(self):
        obj = StructuredName.build("head::tail.a.b.d")
        obj2 = StructuredName.build("head::tail.a.b.c.d")
        assert(not obj < obj2 )


    def test_le_fail_on_self(self):
        obj = StructuredName.build("head::tail.a.b.c")
        obj2 = StructuredName.build("head::tail.a.b.c")
        assert(obj == obj2)
        assert(obj <= obj2 )

    def test_not_le(self):
        obj = StructuredName.build("head::tail.a.b.d")
        obj2 = StructuredName.build("head::tail.a.b.c")
        assert(not obj < obj2 )


    def test_contains(self):
        obj = StructuredName.build("head::tail.a.b.c")
        obj2 = StructuredName.build("head::tail.a.b.c.e")
        assert(obj2 in obj)


    def test_not_contains(self):
        obj = StructuredName.build("head::tail.a.b.c")
        obj2 = StructuredName.build("head::tail.a.b.c.e")
        assert(obj not in obj2)
