#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import warnings
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest

# ##-- end 3rd party imports

printer = logmod.getLogger("doot._printer")

import doot
doot._test_setup()
import doot.errors
from doot.structs import DootKey
from doot.utils.decorators import DecorationUtils

logging = logmod.root

class TestDecorationUtils:

    def test_initial(self):
        assert(DecorationUtils is not None)


    def test_signature(self):
        def test_func(a:int, b:float, c:str) -> int:
            pass

        assert(DecorationUtils.verify_signature(test_func, ["a","b","c"]))


    def test_signature_tail(self):
        def test_func(a:int, b:float, c:str) -> int:
            pass

        assert(DecorationUtils.verify_signature(test_func, ["a"], ["b" ,"c"]))


    def test_signature_fail(self):
        def test_func(a, b, c):
            pass

        assert(not DecorationUtils.verify_signature(test_func, ["a","b","d"]))


    def test_annotate(self):
        def test_func(a, b, c):
            pass

        assert(not hasattr(test_func, DecorationUtils._annot))
        DecorationUtils.annotate(test_func, {"a","b","c"})
        assert(hasattr(test_func, DecorationUtils._annot))


    def test_has_annotations(self):
        def test_func(a, b, c):
            pass

        assert(not DecorationUtils.has_annotations(test_func))
        DecorationUtils.annotate(test_func, {"a","b","c"})
        assert(DecorationUtils.has_annotations(test_func))


    def test_key_annotations(self):
        def test_func(spec, state, a, b, c):
            pass

        assert(not hasattr(test_func, DecorationUtils._keys))
        DecorationUtils._update_key_annotations(test_func, ["a","b","c"])
        assert(hasattr(test_func, DecorationUtils._keys))


    def test_key_annotations_update_correctly(self):
        """
          decorators run in order:
          @last
          @mid
          @first
          def ...


          so annotations are applied in reverse
        """
        def test_func(spec, state, a, b, c):
            pass

        assert(not hasattr(test_func, DecorationUtils._keys))
        DecorationUtils._update_key_annotations(test_func, ["c"])
        assert(len(getattr(test_func, DecorationUtils._keys)) == 1)
        DecorationUtils._update_key_annotations(test_func, ["a", "b"])
        assert(len(getattr(test_func, DecorationUtils._keys)) == 3)
