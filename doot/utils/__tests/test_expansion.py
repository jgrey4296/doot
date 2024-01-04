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
import doot.errors
from doot.control.locations import DootLocations
from doot.structs import DootActionSpec
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
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "bloo"}))

    @pytest.fixture(scope="function")
    def setup_locs(self, mocker):
        new_locs = TomlGuard({"p1": "test1", "p2": "test2/sub"})
        return mocker.patch.object(exp.doot.locs, "_data", new_locs)

    def test_basic_to_str(self, spec):
        result = exp.to_str("{x}", spec, {"x": "blah"})
        assert(result == "blah")

    def test_key_with_hyphen(self, spec):
        result = exp.to_str("{bloo-x}", spec, {"bloo-x": "blah"})
        assert(result == "blah")

    def test_missing_key(self, spec):
        result = exp.to_str("{q}", spec, {"x": "blah"})
        assert(result == "{q}")

    def test_missing_key_any(self, spec):
        result = exp.to_any("{q}", spec, {"x": "blah"})
        assert(result == None)

    def test_missing_key_path(self, spec):
        with pytest.raises(doot.errors.DootLocationError):
            exp.to_path("{q}", spec, {"x": "blah"})

    def test_basic_spec_pre_expand(self, spec):
        """
          z isnt a key, but z_ is, so that is used as the key,
          z_ == bloo, but bloo isn't a key, so {bloo} is returned
        """
        result = exp.to_str("z", spec, {"x": "blah"})
        assert(result == "{bloo}")

    def test_prefer_explicit_key_to_default(self, spec, setup_locs):
        result = exp.to_str("z", spec, {"x": "blah", "z": "aweg", "bloo": "jiojo"})
        assert(result == "jiojo")
        result2 = exp.to_str("x", spec, {"x": "blah", "z": "aweg", "bloo": "jiojo"})
        assert(result2 == "blah")
        result3 = exp.to_path("complex", spec, {"x": "blah", "z": "aweg", "bloo": "jiojo", "complex": "{x}/{bloo}/{p1}" })
        assert(result3.relative_to(pl.Path.cwd()) == pl.Path("blah/jiojo/test1"))
        result4 = exp.to_str("something", spec, {"x": "blah", "z": "aweg", "bloo": "jiojo"})
        assert(result4 == "{something}")
        result5 = exp.to_str("z", spec, {"x": "blah", "z": "aweg", "bloo": "jiojo", "something_": "qqqq"})
        assert(result5 == "jiojo")

    def test_pre_expand_wrap(self, spec):
        result = exp.to_str("z", spec, {"x": "blah"})
        assert(result == "{bloo}")

    def test_wrap(self, spec):
        result = exp.to_str("y", spec, {"x": "blah"})
        assert(result == "aweg")

    def test_actual_indirect_with_spec(self, spec):
        result = exp.to_str("y", spec, {"x": "blah", "y_": "aweg"})
        assert(result == "aweg")

    @pytest.mark.filterwarnings("ignore:.*invalid escape sequence:DeprecationWarning")
    def test_bib_str(self, spec):
        result = exp.to_str("{x}", spec, {"x": r" title        = {Architectonisches Alphabet, bestehend aus drey{\ss}ig Rissen },"})
        assert(result == " title        = {Architectonisches Alphabet, bestehend aus drey{\ss}ig Rissen },")

    @pytest.mark.filterwarnings("ignore:.*invalid escape sequence:DeprecationWarning")
    def test_bib_str_simple(self, spec):
        result = exp.to_str("{x}", spec, {"x": r"\ss"})
        assert(result == "\ss")

    def test_multi_to_str(self, spec):
        result = exp.to_str("{x}:{y}:{x}", spec, {"x": "blah", "y":"bloo"})
        assert(result == "blah:bloo:blah")

    @pytest.mark.xfail
    def test_to_str_fail(self, spec):
        with pytest.raises(TypeError):
            exp.to_str("{x}", spec, {"x": ["blah"]})

    def test_to_path_basic(self, spec, mocker, setup_locs):
        result = exp.to_path("{x}", spec, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")

    def test_to_path_from_path(self, spec, mocker, setup_locs):
        result = exp.to_path(pl.Path("{x}"), spec, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")

    def test_to_path_multi_path_expansion(self, spec, mocker, setup_locs):
        result = exp.to_path(pl.Path("{x}/{different}"), spec, {"x": "blah", "different": "a/b/c"})
        assert(isinstance(result, pl.Path))
        rel = result.relative_to(pl.Path.cwd())
        assert(rel == pl.Path("blah/a/b/c"))

    def test_to_path_with_path_value(self, spec, mocker, setup_locs):
        result = exp.to_path(pl.Path("{x}/{different}"), spec, {"x": "blah", "different": pl.Path("a/b/c")})
        assert(isinstance(result, pl.Path))
        rel = result.relative_to(pl.Path.cwd())
        assert(rel == pl.Path("blah/a/b/c"))

    def test_to_path_with_subexpansion(self, spec, mocker, setup_locs):
        result = exp.to_path(pl.Path("{x}/{different}"), spec, {"x": "blah", "different": pl.Path("a/{x}/c")})
        assert(isinstance(result, pl.Path))
        rel = result.relative_to(pl.Path.cwd())
        assert(rel == pl.Path("blah/a/blah/c"))

    def test_to_path_loc_expansion(self, spec, mocker, setup_locs):
        result = exp.to_path("{p1}", spec, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "test1")

    def test_to_path_multi_expansion(self, spec, mocker, setup_locs):
        result = exp.to_path("{p1}/{x}", spec, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")
        assert(result.parent.stem == "test1")

    def test_to_path_subdir(self, spec, mocker, setup_locs):
        result = exp.to_path("{p2}/{x}", spec, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")
        assert(result.parent.stem == "sub")
        assert(result.parent.parent.stem == "test2")

    def test_to_any_basic(self, spec, mocker, setup_locs):
        result = exp.to_any("{x}", spec, {"x": set([1,2,3])})
        assert(isinstance(result, set))

    def test_to_any_typecheck(self, spec, mocker, setup_locs):
        result = exp.to_any("{x}", spec, {"x": set([1,2,3])}, type_=set)
        assert(isinstance(result, set))

    def test_to_any_typecheck_union(self, spec, mocker, setup_locs):
        result = exp.to_any("{x}", spec, {"x": set([1,2,3])}, type_=set|list)
        assert(isinstance(result, set))

    def test_to_any_typecheck_union_2(self, spec, mocker, setup_locs):
        result = exp.to_any("x", spec, {"x": [1,2,3]}, type_=set|list)
        assert(isinstance(result, list))

    def test_to_any_missing_gives_none(self, spec, mocker, setup_locs):
        result = exp.to_any("z", spec, {}, type_=None)
        assert(result is None)

    def test_to_any_returns_none_or_str(self, spec, mocker, setup_locs):
        result = exp.to_any("z_", spec, {}, type_=str|None)
        assert(result is None)

    def test_to_any_typecheck_fail(self, spec, mocker, setup_locs):
        with pytest.raises(TypeError):
            exp.to_any("{x}", spec, {"x": set([1,2,3])}, type_=list)

    def test_to_any_multikey_fail(self, spec, mocker, setup_locs):
        result = exp.to_any("{x}{x}", spec, {"x": set([1,2,3])})
        assert(result is None)

class TestDootKey:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"x": "aweg", "y_": "a"}))

    @pytest.fixture(scope="function")
    def state(self):
        return {"a": "bloo", "b_": "blee"}

    def test_initial(self):
        example = exp.DootKey("blah")
        assert(isinstance(example, str))
        assert(isinstance(example, exp.DootKey))

    def test_eq(self):
        example = exp.DootKey("blah")
        other   = exp.DootKey("blah")
        assert(example == other)
        assert(example == example)
        assert(example is example)
        assert(example is not other)
        assert(example == "blah")

    def test_contains(self):
        example = exp.DootKey("blah")
        assert(example in "this is a {blah} test")
        assert("blah" in example)

    def test_contain_fail(self):
        example = exp.DootKey("blah")
        assert(example.form not in "this is a blah test")
        assert(example not in "this is a {bloo} test")
        assert("bloo" not in example)

    def test_within(self):
        example = exp.DootKey("blah")
        assert(example.within("this is a {blah} test"))

    def test_within_fail(self):
        example = exp.DootKey("blah")
        assert(not example.within("this is a blah test"))

    def test_within_dict(self):
        example = exp.DootKey("blah")
        assert(example.within({"blah": "aweg"}))

    def test_within_dict_fail(self):
        example = exp.DootKey("blah")
        assert(not example.within({"bloo": "aweg"}))
        assert(not example.within({"{bloo}": "aweg"}))

    def test_make(self):
        example = exp.DootKey.make("blah")
        assert(isinstance(example, str))
        assert(isinstance(example, exp.DootKey))

    def test_make_2(self):
        example = exp.DootKey.make("{blah}")
        assert(isinstance(example, str))
        assert(isinstance(example, exp.DootKey))

    def test_str_call(self):
        example = exp.DootKey("blah")
        assert(str(example) == "blah")


    def test_form(self):
        example = exp.DootKey("blah")
        assert(example.form == "{blah}")

    def test_repr_call(self):
        example = exp.DootKey("blah")
        assert(repr(example) == "<DootKey: blah>")

    def test_indirect(self):
        example = exp.DootKey("blah")
        assert(example.indirect == "blah_")

    def test_expand_nop(self, spec, state):
        example = exp.DootKey("blah")
        result = example.expand(spec, state)
        assert(result == "{blah}")

    def test_expand(self, spec, state):
        example = exp.DootKey("x")
        result = example.expand(spec, state)
        assert(result == "aweg")

    def test_format_nested(self, spec, state):
        example = exp.DootKey("c")
        state['c'] = exp.DootKey("a")
        result = example.expand(spec, state)
        assert(result == "bloo")

    def test_in_dict(self, spec, state):
        example = exp.DootKey("c")
        the_dict = {example : "blah"}
        assert(example in the_dict)

    def test_equiv_in_dict(self, spec, state):
        example = exp.DootKey("c")
        the_dict = {"c": "blah"}
        assert(example in the_dict)

class TestDootMultiKey:

    @pytest.mark.xfail
    def test_initial(self):
        multikey = exp.DootKey.make("a {test} string {multi}")
        assert(isinstance(multikey, exp.DootMultiKey))
