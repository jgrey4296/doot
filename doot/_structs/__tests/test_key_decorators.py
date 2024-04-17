#!/usr/bin/env python1
"""

"""
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import functools as ftz
import warnings

import pytest

logging = logmod.root

import decorator
from tomlguard import TomlGuard
import doot
doot._test_setup()
from doot.control.locations import DootLocations
from doot.structs import DootKey, DootActionSpec
from doot._structs import key as dkey
from doot.utils.decorators import DootDecorator as DDec, DecorationUtils as DecU

KEY_BASES               : Final[str] = ["bob", "bill", "blah", "other"]
MULTI_KEYS              : Final[str] = ["{bob}/{bill}", "{blah}/{bloo}", "{blah}/{bloo}"]
NON_PATH_MUTI_KEYS      : Final[str] = ["{bob}_{bill}", "{blah} <> {bloo}", "! {blah}! {bloo}!"]
KEY_INDIRECTS           : Final[str] = ["bob_", "bill_", "blah_", "other_"]

TEST_LOCS               : Final[DootLocations] = DootLocations(pl.Path.cwd()).update({"blah": "doot"})

class TestKeyDecorators:
    """ Test the key decorators """

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"x": "aweg", "y_": "a"}))

    @pytest.fixture(scope="function")
    def state(self):
        return {"a": "bloo", "b_": "blee", "c": "awegg"}

    def test_verify_signature_basic_with_self(self):

        def an_action(self, spec, state):
            pass

        assert(DecU.verify_action_signature(an_action, []))

    def test_verify_signature_basic_no_self(self):

        def an_action(spec, state):
            pass

        assert(DecU.verify_action_signature(an_action, []))

    def test_verify_signature_fail_wrong_self(self):

        def an_action(notself, spec, state):
            pass

        assert(not DecU.verify_action_signature(an_action, []))

    def test_verify_signature_fail_no_self_wrong_spec(self):

        def an_action(notspec, state):
            pass

        assert(not DecU.verify_action_signature(an_action, []))

    def test_verify_signature_fail_no_self_wrong_state(self):

        def an_action(spec, notstate):
            pass

        assert(not DecU.verify_action_signature(an_action, []))

    def test_verify_signature_with_key(self):

        def an_action(spec, state, x):
            pass

        assert(DecU.verify_action_signature(an_action, ["x"]))

    def test_verify_signature_fail_with_wrong_key(self):

        def an_action(spec, state, x):
            pass

        assert(not DecU.verify_action_signature(an_action, ["y"]))

    def test_verify_signature_with_multi_keys(self):

        def an_action(spec, state, x, y):
            pass

        assert(DecU.verify_action_signature(an_action, ["x", "y"]))

    def test_verify_signature_fail_with_multi_keys(self):

        def an_action(spec, state, x, y):
            pass

        assert(not DecU.verify_action_signature(an_action, ["x", "z"]))

    def test_verify_signature_with_multi_keys_offset(self):

        def an_action(spec, state, x, y):
            pass

        assert(DecU.verify_action_signature(an_action, ["y"]))

    def test_verify_signature_fail_with_multi_keys_offset(self):

        def an_action(spec, state, x, y):
            pass

        assert(not DecU.verify_action_signature(an_action, ["z"]))

class TestKeyDecoratorsCalls:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"x": "aweg", "y_": "a"}))

    @pytest.fixture(scope="function")
    def state(self):
        return {"a": "bloo", "b_": "blee", "c": "awegg"}

    def test_basic_annotate(self):

        def an_action(spec, state, x, y):
            pass
        result = DecU._update_key_annotations(an_action, ["x", "y"])
        assert(result)

    def test_basic_expand(self, spec, state):

        @dkey.DootKey.dec.expands("x")
        def an_action(spec, state, x):
            return x
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result == "aweg")

    def test_expand_fail_with_nonmatching_paramname(self, spec, state):

        with pytest.raises(doot.errors.DootKeyError):

            @dkey.DootKey.dec.expands("x")
            def an_action(spec, state, y):
                return x

    def test_expand_with_underscore_param(self, spec, state):

        @dkey.DootKey.dec.expands("x")
        def an_action(spec, state, _y):
            return _y

        result = an_action(spec, state)
        assert(result == "aweg")

    def test_type_with_underscore_param(self, spec, state):
        state['from'] = "aweg"

        @dkey.DootKey.dec.types("from")
        @dkey.DootKey.dec.types("to")
        def an_action(self, spec, state, _from, to):
            return _from

        result = an_action(None, spec, state)
        assert(result == "aweg")

    def test_basic_method_expand(self, spec, state):

        @dkey.DootKey.dec.expands("x")
        def an_action(self, spec, state, x):
            return x
        assert(an_action.__name__ == "an_action")
        result = an_action(self, spec, state)
        assert(result == "aweg")

    def test_sequence_expand(self, spec, state):

        @dkey.DootKey.dec.expands("x")
        @dkey.DootKey.dec.expands("{c}/blah")
        def an_action(spec, state, x, _y):
            return [x,_y]

        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result[0] == "aweg")
        assert(result[1] == "awegg/blah")


    def test_error_on_non_identifier(self, spec, state):

        with pytest.raises(doot.errors.DootKeyError):
            @dkey.DootKey.dec.expands("{c}/blah")
            def an_action(spec, state, y):
                return y


    def test_multi_expand(self, spec, state):

        @dkey.DootKey.dec.expands("x", "y")
        def an_action(spec, state, x, y):
            return [x,y]
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result[0] == "aweg")
        assert(result[1] == "bloo")

    def test_sequence_multi_expand(self, spec, state):

        @dkey.DootKey.dec.expands("x", "y")
        @dkey.DootKey.dec.expands("a", "c")
        def an_action(spec, state, x, y, a, c):
            return [x,y, a, c]
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result[0] == "aweg")
        assert(result[1] == "bloo")
        assert(result[2] == "bloo")
        assert(result[3] == "awegg")

class TestKeyDecoratorAnnotations:

    def test_verify_signature(self):

        def simple(spec, state):
            pass

        assert(DecU.verify_action_signature(simple, []))

    def test_verify_signature_fail(self):

        def simple(spec, state, blah):
            pass

        assert(not DecU.verify_action_signature(simple, ["bloo"]))

    def test_verify_signature_fail_2(self):

        def simple(spec, state):
            pass

        assert(not DecU.verify_action_signature(simple, ["blah"]))

    def test_verify_signature_decorated(self):

        def mydec(f):

            @ftz.wraps(f)
            def wrapper(spec:dict, state:dict):
                return f(spec, state, state['other'])

            # ftz.update_wrapper(wrapper, f, assigned=ftz.WRAPPER_ASSIGNMENTS, updated=ftz.WRAPPER_UPDATES)
            return wrapper

        @mydec
        def simple(spec:dict, state:dict, other:str):
            pass

        assert(DecU.verify_action_signature(simple, ["spec", "state"]))

    def test_decorate_alt(self):

        def mydec(spec:dict, state:dict):
            return f(spec, state, state['other'])

        mydec = decorator.decorator(mydec, kwsyntax=True)

        @mydec
        def simple(spec:dict, state:dict, other:str):
            pass

        assert(DecU.verify_action_signature(simple, ["other"]))

    def test_annotate_dict(self):

        def simple(spec, state):
            pass

        DecU.annotate(simple, {"_test_annot" : 5})
        assert(simple._test_annot == 5)

    def test_annotate_set(self):

        def simple(spec, state):
            pass

        assert(not hasattr(simple, DecU._annot))
        DecU.annotate(simple, {"test"})
        assert(isinstance(getattr(simple, DecU._annot), set))
        assert("test" in getattr(simple, DecU._annot))

    def test_decorated_annotation(self):

        @decorator.decorator
        def mydec(f, *args, **kwargs):
            return f(*args, **kwargs)

        @mydec
        def simple(spec, state):
            pass

        unwrapped = DecU._unwrap(simple)
        assert(not hasattr(unwrapped, DecU._annot))
        DecU.annotate(unwrapped, {"test"})
        assert(isinstance(getattr(unwrapped, DecU._annot), set))
        assert("test" in getattr(unwrapped, DecU._annot))
