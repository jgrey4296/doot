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
from doot.structs import DKey
from doot.utils.dkey_decorator import DKeyExpansionDecorator as DKexd

logging = logmod.root

class TestDkeyDecorator:

    @pytest.fixture(scope="function")
    def setup(self):
        pass

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass

    def test_initial(self):
        value = DKexd([])
        assert(isinstance(value, DKexd))

    def test_with_key(self):
        value = DKexd([DKey("test")])
        assert(isinstance(value, DKexd))
        assert(bool(value._data))

    def test_apply_mark(self):
        dec = DKexd([])

        def simple(self):
            pass

        assert(not dec._is_marked(simple))
        marked = dec._apply_mark(simple)
        assert(simple is marked)
        assert(dec._is_marked(marked))


    def test_verify_signature_head(self):
        dec = DKexd([])

        def simple(self):
            pass

        assert(dec._verify_signature(simple, ["self"]))


    def test_verify_signature_head_fail(self):
        dec = DKexd([])

        def simple(self):
            pass

        assert(not dec._verify_signature(simple, ["bloo"]))


    def test_verify_signature_multi_head(self):
        dec = DKexd([])

        def simple(self, first, second, third):
            pass

        assert(dec._verify_signature(simple, ["self", "first", "second", "third"]))


    def test_verify_signature_multi_head_fail(self):
        dec = DKexd([])

        def simple(self, first, second, third):
            pass

        assert(not dec._verify_signature(simple, ["self", "first", "bloo", "third"]))


    def test_verify_signature_tail(self):
        dec = DKexd([])

        def simple(self, first, second, third):
            pass

        assert(dec._verify_signature(simple, ["self"], ["third"]))


    def test_verify_signature_multi_tail(self):
        dec = DKexd([])

        def simple(self, first, second, third):
            pass

        assert(dec._verify_signature(simple, ["self"], ["second", "third"]))


    def test_verify_signature_multi_tail_fail(self):
        dec = DKexd([])

        def simple(self, first, second, third):
            pass

        assert(not dec._verify_signature(simple, ["self"], ["first", "bloo", "third"]))


    def test_update_annotations_empty(self):
        dec = DKexd([])

        def simple(self, first, second, third):
            pass

        annots = dec._update_annotations(simple)
        assert(isinstance( annots, list ))
        assert(not bool(annots))


    def test_update_annotations_simple(self):
        dec = DKexd([DKey("first"), DKey("second")])

        def simple(self, first, second, third):
            pass

        annots = dec._update_annotations(simple)
        assert(isinstance( annots, list ))
        assert(bool(annots))


    def test_get_annotations(self):
        dec = DKexd([DKey("first"), DKey("second")])

        def simple(self, first, second, third):
            pass

        annots = dec._update_annotations(simple)
        assert(isinstance( annots, list ))
        assert(bool(annots))
        assert(annots == dec.get_annotations(simple))
