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

import decorator
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

class TestDecorationUtils2:
    """ Test the key decorators """

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"x": "aweg", "y_": "a"}))

    @pytest.fixture(scope="function")
    def state(self):
        return {"a": "bloo", "b_": "blee", "c": "awegg"}

    def test_verify_signature_basic_with_self(self):

        def an_action(self, spec, state):
            pass

        assert(DecorationUtils.verify_action_signature(an_action, []))

    def test_verify_signature_basic_no_self(self):

        def an_action(spec, state):
            pass

        assert(DecorationUtils.verify_action_signature(an_action, []))

    def test_verify_signature_fail_wrong_self(self):

        def an_action(notself, spec, state):
            pass

        assert(not DecorationUtils.verify_action_signature(an_action, []))

    def test_verify_signature_fail_no_self_wrong_spec(self):

        def an_action(notspec, state):
            pass

        assert(not DecorationUtils.verify_action_signature(an_action, []))

    def test_verify_signature_fail_no_self_wrong_state(self):

        def an_action(spec, notstate):
            pass

        assert(not DecorationUtils.verify_action_signature(an_action, []))

    def test_verify_signature_with_key(self):

        def an_action(spec, state, x):
            pass

        assert(DecorationUtils.verify_action_signature(an_action, ["x"]))

    def test_verify_signature_fail_with_wrong_key(self):

        def an_action(spec, state, x):
            pass

        assert(not DecorationUtils.verify_action_signature(an_action, ["y"]))

    def test_verify_signature_with_multi_keys(self):

        def an_action(spec, state, x, y):
            pass

        assert(DecorationUtils.verify_action_signature(an_action, ["x", "y"]))

    def test_verify_signature_fail_with_multi_keys(self):

        def an_action(spec, state, x, y):
            pass

        assert(not DecorationUtils.verify_action_signature(an_action, ["x", "z"]))

    def test_verify_signature_with_multi_keys_offset(self):

        def an_action(spec, state, x, y):
            pass

        assert(DecorationUtils.verify_action_signature(an_action, ["y"]))

    def test_verify_signature_fail_with_multi_keys_offset(self):

        def an_action(spec, state, x, y):
            pass

        assert(not DecorationUtils.verify_action_signature(an_action, ["z"]))

class TestKeyDecoratorAnnotations:

    def test_verify_signature(self):

        def simple(spec, state):
            pass

        assert(DecorationUtils.verify_action_signature(simple, []))

    def test_verify_signature_fail(self):

        def simple(spec, state, blah):
            pass

        assert(not DecorationUtils.verify_action_signature(simple, ["bloo"]))

    def test_verify_signature_fail_2(self):

        def simple(spec, state):
            pass

        assert(not DecorationUtils.verify_action_signature(simple, ["blah"]))

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

        assert(DecorationUtils.verify_action_signature(simple, ["spec", "state"]))

    def test_decorate_alt(self):

        def mydec(spec:dict, state:dict):
            return f(spec, state, state['other'])

        mydec = decorator.decorator(mydec, kwsyntax=True)

        @mydec
        def simple(spec:dict, state:dict, other:str):
            pass

        assert(DecorationUtils.verify_action_signature(simple, ["other"]))

    def test_annotate_dict(self):

        def simple(spec, state):
            pass

        DecorationUtils.annotate(simple, {"_test_annot" : 5})
        assert(simple._test_annot == 5)

    def test_annotate_set(self):

        def simple(spec, state):
            pass

        assert(not hasattr(simple, DecorationUtils._annot))
        DecorationUtils.annotate(simple, {"test"})
        assert(isinstance(getattr(simple, DecorationUtils._annot), set))
        assert("test" in getattr(simple, DecorationUtils._annot))

    def test_decorated_annotation(self):

        @decorator.decorator
        def mydec(f, *args, **kwargs):
            return f(*args, **kwargs)

        @mydec
        def simple(spec, state):
            pass

        unwrapped = DecorationUtils.unwrap(simple)
        assert(not hasattr(unwrapped, DecorationUtils._annot))
        DecorationUtils.annotate(unwrapped, {"test"})
        assert(isinstance(getattr(unwrapped, DecorationUtils._annot), set))
        assert("test" in getattr(unwrapped, DecorationUtils._annot))
