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

from tomlguard import TomlGuard
import doot
from doot.control.locations import DootLocations
from doot.structs import DootKey, DootActionSpec
from doot._structs import key as dkey

KEY_BASES               : Final[str] = ["bob", "bill", "blah", "other"]
MULTI_KEYS              : Final[str] = ["{bob}/{bill}", "{blah}/{bloo}", "{blah}/{bloo}"]
NON_PATH_MUTI_KEYS      : Final[str] = ["{bob}_{bill}", "{blah} <> {bloo}", "! {blah}! {bloo}!"]
KEY_INDIRECTS           : Final[str] = ["bob_", "bill_", "blah_", "other_"]

TEST_LOCS               : Final[DootLocations] = DootLocations(pl.Path.cwd()).update({"blah": "doot"})

class TestKeyConstruction:

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_base_key(self, name):
        obj = dkey.DootSimpleKey(name)
        assert(isinstance(obj, DootKey))
        assert(isinstance(obj, str))

    @pytest.mark.parametrize("name", MULTI_KEYS)
    def test_multi_key(self, name):
        obj = dkey.DootMultiKey(name)
        assert(isinstance(obj, DootKey))
        assert(isinstance(obj, dkey.DootMultiKey))
        assert(not isinstance(obj, str))

    def test_multi(self):
        obj = dkey.DootMultiKey("{blah}/{bloo}")
        assert(isinstance(obj, DootKey))
        assert(isinstance(obj, dkey.DootMultiKey))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_make(self, name):
        obj = DootKey.make(name)
        assert(isinstance(obj, DootKey))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_make_idempotent(self, name):
        obj1 = DootKey.make(name)
        obj2 = DootKey.make(obj1)
        assert(isinstance(obj1, DootKey))
        assert(isinstance(obj2, DootKey))
        assert(obj1 == obj2)

    @pytest.mark.parametrize("name", MULTI_KEYS + NON_PATH_MUTI_KEYS)
    def test_multi_make(self, name):
        obj = dkey.DootKey.make(name, strict=False)
        assert(isinstance(obj, DootKey))
        assert(isinstance(obj, dkey.DootMultiKey))

class TestSimpleKey:

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_eq(self, name):
        obj = dkey.DootSimpleKey(name)
        assert(obj == name)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_form(self, name):
        obj = dkey.DootSimpleKey(name)
        assert(obj.form.startswith("{"))
        assert(obj.form.endswith("}"))

    @pytest.mark.parametrize("name,target,within", [("bob", "{bob}", True), ("bob", "bob", False)])
    def test_within(self, name, target, within):
        obj = dkey.DootSimpleKey(name)
        assert(obj.within(target) == within)

    @pytest.mark.parametrize("name", KEY_INDIRECTS)
    def test_is_indirect(self, name):
        obj = dkey.DootSimpleKey(name)
        assert(isinstance(obj, DootKey))
        assert(obj.is_indirect)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_not_is_indirect(self, name):
        obj = dkey.DootSimpleKey(name)
        assert(isinstance(obj, DootKey))
        assert(not obj.is_indirect)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_hash(self, name):
        obj = dkey.DootSimpleKey(name)
        assert(isinstance(obj, DootKey))
        assert(hash(name) == hash(name))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_indirect(self, name):
        obj = dkey.DootSimpleKey(name)
        assert(not obj.indirect.endswith("__"))

    @pytest.mark.parametrize("name", KEY_INDIRECTS)
    def test_indirect_idempotent(self, name):
        assert(name.endswith("_"))
        obj = dkey.DootSimpleKey(name)
        assert(not obj.indirect.endswith("__"))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_redirect(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(kwargs={f"{name}_": "blah"}, spec=DootActionSpec)
        assert(obj.indirect in spec.kwargs)
        result        = obj.redirect(spec)
        assert(isinstance(result, DootKey))
        assert(result == "blah")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_redirect_to_list_fail(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(kwargs={f"{name}_": ["blah", "bloo"]}, spec=DootActionSpec)
        assert(obj.indirect in spec.kwargs)
        with pytest.raises(TypeError):
            result        = obj.redirect(spec)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(kwargs={f"{name}_": ["blah", "bloo"]}, spec=DootActionSpec)
        assert(obj.indirect in spec.kwargs)
        result        = obj.redirect_multi(spec)
        assert(isinstance(result, list))
        assert(all((isinstance(x, DootKey) for x in result)))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expand_from_spec(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(kwargs={f"{obj}": "blah"}, spec=DootActionSpec)
        result        = obj.expand(spec, {})
        assert(result == "blah")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expand_from_state(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(kwargs={}, spec=DootActionSpec)
        state         = {f"{obj}": "blah"}
        result        = obj.expand(spec, state)
        assert(result == "blah")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expansion_prefers_spec_over_state(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(kwargs={f"{obj}": "bloo"}, spec=DootActionSpec)
        state         = {f"{obj}": "blah"}
        result        = obj.expand(spec, state)
        assert(result == "bloo")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expansion_prefers_redirect_over_other(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(kwargs={"aweg": "bloo", obj.indirect : "aweg"}, spec=DootActionSpec)
        state         = {f"{obj}": "blah"}
        result        = obj.expand(spec, state)
        assert(result == "bloo")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expansion_of_missing_returns_form(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(kwargs={}, spec=DootActionSpec)
        state         = {}
        result        = obj.expand(spec, state)
        assert(result == obj.form)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_recursive_expansion(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(kwargs={f"{name}": dkey.DootSimpleKey("key1")}, spec=DootActionSpec)
        state         = {"key1": dkey.DootSimpleKey("key2"), "key2": "aweg"}
        result        = obj.expand(spec, state)
        assert(result == "aweg")

    @pytest.mark.parametrize("name", KEY_BASES)
    @pytest.mark.parametrize("value,type", [([1,2,3], list)])
    def test_expansion_flattening(self, mocker, name, value, type):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(kwargs={}, spec=DootActionSpec)
        state         = {name: value}
        result        = obj.expand(spec, state)
        assert(isinstance(result, str))
        assert(result == str(value))

    @pytest.mark.parametrize("name", KEY_BASES)
    @pytest.mark.parametrize("value,type", [([1,2,3], list)])
    def test_to_type_expansion(self, mocker, name, value, type):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(kwargs={}, spec=DootActionSpec)
        state         = {name: value}
        result        = obj.to_type(spec, state)
        assert(isinstance(result, type))
        assert(result == value)

    @pytest.mark.parametrize("name", KEY_BASES)
    @pytest.mark.parametrize("value,type", [([1,2,3], list)])
    def test_to_type_on_fail(self, mocker, name, value, type):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(kwargs={}, spec=DootActionSpec)
        state         = {}
        result        = obj.to_type(spec, state, on_fail="blah")
        # assert(isinstance(result, type))
        assert(result == "blah")

    @pytest.mark.parametrize("name", KEY_BASES)
    @pytest.mark.parametrize("value,type", [([1,2,3], list)])
    def test_to_type_on_fail_nop(self, mocker, name, value, type):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(kwargs={}, spec=DootActionSpec)
        state         = {name : value}
        result        = obj.to_type(spec, state, on_fail="blah")
        # assert(isinstance(result, type))
        assert(result == value)

    @pytest.mark.parametrize("key,target", [("blah", "./doot")])
    def test_to_path_expansion(self, mocker, key, target):
        mocker.patch.dict("doot.__dict__", locs=TEST_LOCS)
        obj           = DootKey.make(key)
        spec          = mocker.Mock(kwargs={}, spec=DootActionSpec)
        state         = {}
        result        = obj.to_path(spec, state)
        assert(isinstance(result, pl.Path))
        assert(result == pl.Path(target).expanduser().resolve())

class TestSimpleKey2:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"x": "aweg", "y_": "a"}))

    @pytest.fixture(scope="function")
    def state(self):
        return {"a": "bloo", "b_": "blee"}

    def test_basic_expand(self):
        example = DootKey.make("blah")
        assert(isinstance(example, str))
        assert(isinstance(example, DootKey))

    def test_eq(self):
        example = DootKey.make("blah")
        other   = DootKey.make("blah")
        assert(example == other)
        assert(example == example)
        assert(example is example)
        assert(example is not other)
        assert(example == "blah")

    def test_contains(self):
        example = DootKey.make("blah")
        assert(example in "this is a {blah} test")
        assert("blah" in example)

    def test_contain_fail(self):
        example = DootKey.make("blah")
        assert(example.form not in "this is a blah test")
        assert(example not in "this is a {bloo} test")
        assert("bloo" not in example)

    def test_within(self):
        example = DootKey.make("blah")
        assert(example.within("this is a {blah} test"))

    def test_within_fail(self):
        example = DootKey.make("blah")
        assert(not example.within("this is a blah test"))

    def test_within_dict(self):
        example = DootKey.make("blah")
        assert(example.within({"blah": "aweg"}))

    def test_within_dict_fail(self):
        example = DootKey.make("blah")
        assert(not example.within({"bloo": "aweg"}))
        assert(not example.within({"{bloo}": "aweg"}))

    def test_str_call(self):
        example = DootKey.make("blah")
        assert(str(example) == "blah")

    def test_form(self):
        example = DootKey.make("blah")
        assert(example.form == "{blah}")

    def test_repr_call(self):
        example = DootKey.make("blah")
        assert(repr(example) == "<DootSimpleKey: blah>")

    def test_indirect(self):
        example = DootKey.make("blah")
        assert(example.indirect == "blah_")

    def test_expand_nop(self, spec, state):
        example = DootKey.make("blah")
        result = example.expand(spec, state)
        assert(result == "{blah}")

    def test_expand(self, spec, state):
        example       = DootKey.make("x")
        result        = example.expand(spec, state)
        assert(result == "aweg")

    def test_format_nested(self, spec, state):
        example = DootKey.make("c")
        state['c'] = DootKey.make("a")
        result = example.expand(spec, state)
        assert(result == "bloo")

    def test_in_dict(self, spec, state):
        example = DootKey.make("c")
        the_dict = {example : "blah"}
        assert(example in the_dict)

    def test_equiv_in_dict(self, spec, state):
        example = DootKey.make("c")
        the_dict = {"c": "blah"}
        assert(example in the_dict)

    @pytest.mark.parametrize("name", MULTI_KEYS + NON_PATH_MUTI_KEYS)
    def test_set_default_expansion(self, spec, state, name):
        obj = dkey.DootKey.make(name, strict=False)
        obj.set_expansion_hint("str")
        assert(isinstance(obj(spec, state), str))

class TestMultiKey:

    @pytest.mark.parametrize("key,targets", [("{blah} test", ["blah"]), ("{blah} {bloo}", ["blah", "bloo"]), ("{blah} {blah}", ["blah"])])
    def test_keys(self, key, targets):
        obj           = DootKey.make(key, strict=False)
        assert(obj.keys() == set(targets))

    @pytest.mark.parametrize("key,target", [("{blah}/bloo", "./doot/bloo"), ("{blah}/bloo/{aweg}", "./doot/bloo/qqqq") ])
    def test_to_path_expansion(self, mocker, key, target):
        mocker.patch.dict("doot.__dict__", locs=TEST_LOCS)
        obj           = DootKey.make(key, strict=False)
        spec          = mocker.Mock(kwargs={}, spec=DootActionSpec)
        state         = {"aweg": "qqqq"}
        result        = obj.to_path(spec, state)
        assert(isinstance(result, pl.Path))
        assert(result == pl.Path(target).expanduser().resolve())

    @pytest.mark.parametrize("key,target", [("{blah}/bloo", "doot/bloo"), ("test !!! {blah}", "test !!! doot"), ("{aweg}-{blah}", "BOO-doot") ])
    def test_expansion(self, mocker, key, target):
        obj           = DootKey.make(key, strict=False)
        spec          = mocker.Mock(kwargs={}, spec=DootActionSpec)
        state         = {"blah": "doot", "aweg": "BOO"}
        result        = obj.expand(spec, state)
        assert(isinstance(result, str))
        assert(result == target)

class TestStringExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "bloo"}))

    @pytest.fixture(scope="function")
    def setup_locs(self, mocker):
        new_locs = TomlGuard({"p1": "test1", "p2": "test2/sub"})
        return mocker.patch.object(doot.locs, "_data", new_locs)

    def test_basic_to_str(self, spec):
        result = DootKey.make("{x}").expand(spec, {"x": "blah"})
        assert(result == "blah")

    def test_key_with_hyphen(self, spec):
        result = DootKey.make("{bloo-x}").expand(spec, {"bloo-x": "blah"})
        assert(result == "blah")

    def test_missing_key(self, spec):
        result = DootKey.make("{q}").expand(spec, {"x": "blah"})
        assert(result == "{q}")

    def test_basic_spec_pre_expand(self, spec):
        """
          z isnt a key, but z_ is, so that is used as the key,
          z_ == bloo, but bloo isn't a key, so {bloo} is returned
        """
        result = DootKey.make("z").expand(spec, {"x": "blah"})
        assert(result == "{bloo}")

    @pytest.mark.parametrize("key,target,state", [
        ("z", "jiojo", {"x": "blah", "z": "aweg", "bloo": "jiojo"}),
        ("x", "blah", {"x": "blah", "z": "aweg", "bloo": "jiojo"}),
        ("something", "{something}", {"x": "blah", "z": "aweg", "bloo": "jiojo"}),
        ("z", "jiojo", {"x": "blah", "z": "aweg", "bloo": "jiojo", "something_": "qqqq"}),
                             ])
    def test_prefer_explicit_key_to_default(self, spec, setup_locs, key, target, state):
        result = DootKey.make(key).expand(spec, state)
        assert(result == target)

    def test_pre_expand_wrap(self, spec):
        result = DootKey.make("z").expand(spec, {"x": "blah"})
        assert(result == "{bloo}")

    def test_wrap(self, spec):
        result = DootKey.make("y").expand(spec, {"x": "blah"})
        assert(result == "aweg")

    def test_actual_indirect_with_spec(self, spec):
        result = DootKey.make("y").expand(spec, {"x": "blah", "y_": "aweg"})
        assert(result == "aweg")

    @pytest.mark.filterwarnings("ignore:.*invalid escape sequence:DeprecationWarning")
    def test_bib_str(self, spec):
        result = DootKey.make("{x}").expand(spec, {"x": r" title        = {Architectonisches Alphabet, bestehend aus drey{\ss}ig Rissen },"})
        assert(result == r" title        = {Architectonisches Alphabet, bestehend aus drey{\ss}ig Rissen },")

    @pytest.mark.filterwarnings("ignore:.*invalid escape sequence:DeprecationWarning")
    def test_bib_str_simple(self, spec):
        result = DootKey.make("{x}").expand(spec, {"x": r"\ss"})
        assert(result == r"\ss")

    def test_multi_to_str(self, spec):
        result = DootKey.make("{x}:{y}:{x}", strict=False).expand(spec, {"x": "blah", "y":"bloo"})
        assert(result == "blah:aweg:blah")

    def test_path_as_str(self, spec, setup_locs):
        key = DootKey.make("{p2}/{x}")
        result = key.expand(spec, {"x": "blah", "y":"bloo"}, locs=doot.locs)
        assert(result.endswith("test2/sub/blah"))

    def test_expansion_to_false(self, spec, setup_locs):
        key = DootKey.make("{aFalse}")
        result = key.expand(spec, {"aFalse": False})
        assert(result == "False")

    @pytest.mark.xfail
    def test_to_str_fail(self, spec):
        with pytest.raises(TypeError):
            DootKey.make("{x}").expand(spec, {"x": ["blah"]})

class TestPathExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "bloo"}))

    @pytest.fixture(scope="function")
    def setup_locs(self, mocker):
        new_locs = TomlGuard({"p1": "test1", "p2": "test2/sub"})
        return mocker.patch.object(doot.locs, "_data", new_locs)

    @pytest.mark.parametrize("key,target,state", [("{x}", "blah", {"x": "blah"})])
    def test_to_path_basic(self, spec, mocker, setup_locs, key, target,state):
        obj = DootKey.make(key)
        result = obj.to_path(spec, state)
        assert(isinstance(result, pl.Path))
        assert(result.stem == target)

    def test_to_path_from_path(self, spec, mocker, setup_locs):
        result = DootKey.make(pl.Path("{x}"), strict=False).to_path(spec, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")

    def test_to_path_multi_path_expansion(self, spec, mocker, setup_locs):
        result = DootKey.make(pl.Path("{x}/{different}"), strict=False).to_path(spec, {"x": "blah", "different": "a/b/c"})
        assert(isinstance(result, pl.Path))
        rel = result.relative_to(pl.Path.cwd())
        assert(rel == pl.Path("blah/a/b/c"))

    def test_to_path_with_path_value(self, spec, mocker, setup_locs):
        result = DootKey.make(pl.Path("{x}/{different}"), strict=False).to_path(spec, {"x": "blah", "different": pl.Path("a/b/c")})
        assert(isinstance(result, pl.Path))
        rel = result.relative_to(pl.Path.cwd())
        assert(rel == pl.Path("blah/a/b/c"))

    def test_to_path_with_subexpansion(self, spec, mocker, setup_locs):
        result = DootKey.make(pl.Path("{x}/{different}"), strict=False).to_path(spec, {"x": "blah", "different": pl.Path("a/{x}/c")})
        assert(isinstance(result, pl.Path))
        rel = result.relative_to(pl.Path.cwd())
        assert(rel == pl.Path("blah/a/blah/c"))

    def test_to_path_loc_expansion(self, spec, mocker, setup_locs):
        result = DootKey.make("{p1}").to_path(spec, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "test1")

    def test_to_path_multi_expansion(self, spec, mocker, setup_locs):
        result = DootKey.make("{p1}/{x}", strict=False).to_path(spec, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")
        assert(result.parent.stem == "test1")

    def test_to_path_subdir(self, spec, mocker, setup_locs):
        result = DootKey.make("{p2}/{x}", strict=False).to_path(spec, {"x": "blah"})
        assert(isinstance(result, pl.Path))
        assert(result.stem == "blah")
        assert(result.parent.stem == "sub")
        assert(result.parent.parent.stem == "test2")

    def test_missing_key_path(self, spec):
        key = DootKey.make("{q}", explicit=True)
        with pytest.raises(doot.errors.DootLocationError):
            key.to_path(spec, {"x": "blah"})

    def test_to_path_on_fail(self, spec):
        key = DootKey.make("{q}", explicit=True)
        result = key.to_path(spec, {"x": "blah"}, on_fail="qqqq")
        assert(isinstance(result, pl.Path))
        assert(result.name == "qqqq")

    def test_to_path_on_fail_existing_loc(self, spec, setup_locs):
        key = DootKey.make("{q}", explicit=True)
        result = key.to_path(spec, {"x": "blah"}, on_fail=DootKey.make("p2"))
        assert(isinstance(result, pl.Path))
        assert(result.parent.name == "test2")
        assert(result.name == "sub")

    def test_to_path_nop(self, spec):
        key = DootKey.make("{q}", explicit=True)
        result = key.to_path(spec, {"x": "blah"}, on_fail="blah")
        assert(result.name == "blah")

    def test_chain(self, spec):
        key = DootKey.make("{q}", explicit=True)
        result = key.to_path(spec, {"x": "blah"}, chain=[DootKey.make("t"), DootKey.make("x")])
        assert(isinstance(result, pl.Path))
        assert(result.name == "blah")

    def test_chain_nop(self, spec, setup_locs):
        key = DootKey.make("{p1}", explicit=True)
        result = key.to_path(spec, {"x": "blah"}, chain=[DootKey.make("t"), DootKey.make("x")])
        assert(isinstance(result, pl.Path))
        assert(result.name == "test1")

    def test_chain_into_on_fail(self, spec, setup_locs):
        key = DootKey.make("{nothing}", explicit=True)
        result = key.to_path(spec, {"x": "blah"}, chain=[DootKey.make("t"), DootKey.make("aweg")], on_fail=DootKey.make("p2"))
        assert(isinstance(result, pl.Path))
        assert(result.name == "sub")

    def test_expansion_extra(self, spec, setup_locs):
        key = DootKey.make("{p1}/blah/{y}/{aweg}", strict=False)
        assert(isinstance(key, DootKey))
        state = {"aweg": "doot"}
        result  = key.to_path(spec, state)
        assert(result == pl.Path("test1/blah/aweg/doot").expanduser().resolve())

    def test_expansion_with_ext(self, spec, setup_locs):
        key = DootKey.make("{y}.bib", strict=False)
        assert(isinstance(key, DootKey))
        state = {"aweg": "doot"}
        result  = key.to_path(spec, state)
        assert(result.name == "aweg.bib")

    @pytest.mark.xfail
    def test_expansion_redirect(self, spec, setup_locs):
        key = DootKey.make("aweg_", strict=False)
        assert(isinstance(key, DootKey))
        state = {"aweg": "p2"}
        result  = key.to_path(spec, state)
        assert(result == pl.Path("test2/sub").expanduser().resolve())

    @pytest.mark.parametrize("key,target,state", [("complex", "blah/jiojo/test1", {"x": "blah", "z": "aweg", "bloo": "jiojo", "complex": "{x}/{bloo}/{p1}" })])
    def test_path_expansion_rec(self, spec, setup_locs, key, target,  state):
        key_obj = DootKey.make(key)
        result = key_obj.to_path(spec, state)
        assert(result.relative_to(pl.Path.cwd()) == pl.Path(target))

class TestTypeExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "bloo"}))

    @pytest.fixture(scope="function")
    def setup_locs(self, mocker):
        new_locs = TomlGuard({"p1": "test1", "p2": "test2/sub"})
        return mocker.patch.object(doot.locs, "_data", new_locs)

    def test_to_any_basic(self, spec, mocker, setup_locs):
        result = DootKey.make("{x}").to_type(spec, {"x": set([1,2,3])})
        assert(isinstance(result, set))

    def test_to_any_typecheck(self, spec, mocker, setup_locs):
        result = DootKey.make("{x}").to_type(spec, {"x": set([1,2,3])}, type_=set)
        assert(isinstance(result, set))

    def test_to_any_typecheck_union(self, spec, mocker, setup_locs):
        result = DootKey.make("{x}").to_type(spec, {"x": set([1,2,3])}, type_=set|list)
        assert(isinstance(result, set))

    def test_to_any_typecheck_union_2(self, spec, mocker, setup_locs):
        result = DootKey.make("x").to_type(spec, {"x": [1,2,3]}, type_=set|list)
        assert(isinstance(result, list))

    def test_to_any_missing_gives_none(self, spec, mocker, setup_locs):
        result = DootKey.make("z").to_type(spec, {}, type_=None)
        assert(result is None)

    def test_to_any_returns_none_or_str(self, spec, mocker, setup_locs):
        result = DootKey.make("z_").to_type(spec, {}, type_=str|None)
        assert(result is None)

    def test_to_any_typecheck_fail(self, spec, mocker, setup_locs):
        with pytest.raises(TypeError):
            DootKey.make("{x}").to_type(spec, {"x": set([1,2,3])}, type_=list)

    def test_to_any_multikey_fail(self, spec, mocker, setup_locs):
        with pytest.raises(TypeError):
            DootKey.make("{x}{x}", strict=False).to_type(spec, {"x": set([1,2,3])})

    def test_missing_key_any(self, spec):
        result = DootKey.make("{q}").to_type(spec, {"x": "blah"})
        assert(result == None)

    def test_missing_key_to_on_fail(self, spec):
        result = DootKey.make("{q}").to_type(spec, {"x": "blah"}, on_fail=2)
        assert(result == 2)

    def test_on_fail_nop(self, spec):
        result = DootKey.make("{x}").to_type(spec, {"x": "blah"}, on_fail=2)
        assert(result == "blah")

    def test_chain(self, spec):
        result = DootKey.make("{nothing}").to_type(spec, {"x": "blah"}, chain=[DootKey.make("also_no"), DootKey.make("x")])
        assert(result == "blah")

    def test_chain_into_on_fail(self, spec):
        result = DootKey.make("{nothing}").to_type(spec, {"x": "blah"}, chain=[DootKey.make("also_no"), DootKey.make("xawegw")], on_fail=2)
        assert(result == 2)

class TestKeyWrap:
    """ Test the key decorators """

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"x": "aweg", "y_": "a"}))

    @pytest.fixture(scope="function")
    def state(self):
        return {"a": "bloo", "b_": "blee", "c": "awegg"}

    def test_check_keys_basic_with_self(self):

        def an_action(self, spec, state):
            pass

        assert(dkey.DootKey.kwrap._check_keys(an_action, []))

    def test_check_keys_basic_no_self(self):

        def an_action(spec, state):
            pass

        assert(dkey.DootKey.kwrap._check_keys(an_action, []))

    def test_check_keys_fail_wrong_self(self):

        def an_action(notself, spec, state):
            pass

        assert(not dkey.DootKey.kwrap._check_keys(an_action, []))

    def test_check_keys_fail_no_self_wrong_spec(self):

        def an_action(notspec, state):
            pass

        assert(not dkey.DootKey.kwrap._check_keys(an_action, []))

    def test_check_keys_fail_no_self_wrong_state(self):

        def an_action(spec, notstate):
            pass

        assert(not dkey.DootKey.kwrap._check_keys(an_action, []))

    def test_check_keys_with_key(self):

        def an_action(spec, state, x):
            pass

        assert(dkey.DootKey.kwrap._check_keys(an_action, ["x"]))

    def test_check_keys_fail_with_wrong_key(self):

        def an_action(spec, state, x):
            pass

        assert(not dkey.DootKey.kwrap._check_keys(an_action, ["y"]))

    def test_check_keys_with_multi_keys(self):

        def an_action(spec, state, x, y):
            pass

        assert(dkey.DootKey.kwrap._check_keys(an_action, ["x", "y"]))

    def test_check_keys_fail_with_multi_keys(self):

        def an_action(spec, state, x, y):
            pass

        assert(not dkey.DootKey.kwrap._check_keys(an_action, ["x", "z"]))

    def test_check_keys_with_multi_keys_offset(self):

        def an_action(spec, state, x, y):
            pass

        assert(dkey.DootKey.kwrap._check_keys(an_action, ["y"], offset=1))

    def test_check_keys_fail_with_multi_keys_offset(self):

        def an_action(spec, state, x, y):
            pass

        assert(not dkey.DootKey.kwrap._check_keys(an_action, ["z"], offset=1))

    def test_basic_annotate(self):

        def an_action(spec, state, x, y):
            pass
        result = dkey.DootKey.kwrap._annotate_keys(an_action, ["x", "y"])
        assert(result)

    def test_basic_expand(self, spec, state):

        @dkey.DootKey.kwrap.expands("x")
        def an_action(spec, state, x):
            return x
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result == "aweg")

    def test_basic_method_expand(self, spec, state):

        @dkey.DootKey.kwrap.expands("x")
        def an_action(self, spec, state, x):
            return x
        assert(an_action.__name__ == "an_action")
        result = an_action(self, spec, state)
        assert(result == "aweg")

    def test_sequence_expand(self, spec, state):

        @dkey.DootKey.kwrap.expands("x")
        @dkey.DootKey.kwrap.expands("{c}/blah")
        def an_action(spec, state, x, y):
            return [x,y]
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result[0] == "aweg")
        assert(result[1] == "awegg/blah")

    def test_multi_expand(self, spec, state):

        @dkey.DootKey.kwrap.expands("x", "y")
        def an_action(spec, state, x, y):
            return [x,y]
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result[0] == "aweg")
        assert(result[1] == "bloo")

    def test_sequence_multi_expand(self, spec, state):

        @dkey.DootKey.kwrap.expands("x", "y")
        @dkey.DootKey.kwrap.expands("a", "c")
        def an_action(spec, state, x, y, a, c):
            return [x,y, a, c]
        assert(an_action.__name__ == "an_action")
        result = an_action(spec, state)
        assert(result[0] == "aweg")
        assert(result[1] == "bloo")
        assert(result[2] == "bloo")
        assert(result[3] == "awegg")
