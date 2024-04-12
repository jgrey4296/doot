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
doot._test_setup()
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
    def test_build(self, name):
        obj = DootKey.build(name)
        assert(isinstance(obj, DootKey))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_build_idempotent(self, name):
        obj1 = DootKey.build(name)
        obj2 = DootKey.build(obj1)
        assert(isinstance(obj1, DootKey))
        assert(isinstance(obj2, DootKey))
        assert(obj1 == obj2)

    @pytest.mark.parametrize("name", MULTI_KEYS + NON_PATH_MUTI_KEYS)
    def test_multi_build(self, name):
        obj = dkey.DootKey.build(name, strict=False)
        assert(isinstance(obj, DootKey))
        assert(isinstance(obj, dkey.DootMultiKey))

class TestSimpleGet:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "bloo", "a": 2}))

    def test_initial(self, spec):
        key = DootKey.build("z_")
        result = key.basic(spec, {})
        assert(str(key) == "z_")
        assert(result == "bloo")

    def test_basic(self, spec):
        key = DootKey.build("y")
        result = key.basic(spec, {})
        assert(str(key) == "y")
        assert(result == "aweg")

    def test_another(self, spec):
        key = DootKey.build("a")
        result = key.basic(spec, {})
        assert(str(key) == "a")
        assert(result == 2)

class TestKeyParameterized:

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
        spec          = mocker.Mock(params={f"{name}_": "blah"}, spec=DootActionSpec)
        assert(obj.indirect in spec.params)
        result        = obj.redirect(spec)
        assert(isinstance(result, DootKey))
        assert(result == "blah")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_redirect_to_list_fail(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(params={f"{name}_": ["blah", "bloo"]}, spec=DootActionSpec)
        assert(obj.indirect in spec.params)
        with pytest.raises(TypeError):
            result        = obj.redirect(spec)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(params={f"{name}_": ["blah", "bloo"]}, spec=DootActionSpec)
        assert(obj.indirect in spec.params)
        result        = obj.redirect_multi(spec)
        assert(isinstance(result, list))
        assert(all((isinstance(x, DootKey) for x in result)))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expand_from_spec(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(params={f"{obj}": "blah"}, spec=DootActionSpec)
        result        = obj.expand(spec, {})
        assert(result == "blah")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expand_from_state(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(params={}, spec=DootActionSpec)
        state         = {f"{obj}": "blah"}
        result        = obj.expand(spec, state)
        assert(result == "blah")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expansion_prefers_spec_over_state(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(params={f"{obj}": "bloo"}, spec=DootActionSpec)
        state         = {f"{obj}": "blah"}
        result        = obj.expand(spec, state)
        assert(result == "bloo")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expansion_prefers_redirect_over_other(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(params={"aweg": "bloo", obj.indirect : "aweg"}, spec=DootActionSpec)
        state         = {f"{obj}": "blah"}
        result        = obj.expand(spec, state)
        assert(result == "bloo")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expansion_of_missing_returns_form(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(params={}, spec=DootActionSpec)
        state         = {}
        result        = obj.expand(spec, state)
        assert(result == obj.form)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_recursive_expansion(self, mocker, name):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(params={f"{name}": dkey.DootSimpleKey("key1")}, spec=DootActionSpec)
        state         = {"key1": dkey.DootSimpleKey("key2"), "key2": "aweg"}
        result        = obj.expand(spec, state)
        assert(result == "aweg")

    @pytest.mark.parametrize("name", KEY_BASES)
    @pytest.mark.parametrize("value,type", [([1,2,3], list)])
    def test_expansion_flattening(self, mocker, name, value, type):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(params={}, spec=DootActionSpec)
        state         = {name: value}
        result        = obj.expand(spec, state)
        assert(isinstance(result, str))
        assert(result == str(value))

    @pytest.mark.parametrize("name", KEY_BASES)
    @pytest.mark.parametrize("value,type", [([1,2,3], list)])
    def test_to_type_expansion(self, mocker, name, value, type):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(params={}, spec=DootActionSpec)
        state         = {name: value}
        result        = obj.to_type(spec, state)
        assert(isinstance(result, type))
        assert(result == value)

    @pytest.mark.parametrize("name", KEY_BASES)
    @pytest.mark.parametrize("value,type", [([1,2,3], list)])
    def test_to_type_on_fail(self, mocker, name, value, type):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(params={}, spec=DootActionSpec)
        state         = {}
        result        = obj.to_type(spec, state, on_fail="blah")
        # assert(isinstance(result, type))
        assert(result == "blah")

    @pytest.mark.parametrize("name", KEY_BASES)
    @pytest.mark.parametrize("value,type", [([1,2,3], list)])
    def test_to_type_on_fail_nop(self, mocker, name, value, type):
        obj           = dkey.DootSimpleKey(name)
        spec          = mocker.Mock(params={}, spec=DootActionSpec)
        state         = {name : value}
        result        = obj.to_type(spec, state, on_fail="blah")
        # assert(isinstance(result, type))
        assert(result == value)

    @pytest.mark.parametrize("key,target", [("blah", "./doot")])
    def test_to_path_expansion(self, mocker, key, target):
        mocker.patch.dict("doot.__dict__", locs=TEST_LOCS)
        obj           = DootKey.build(key)
        spec          = mocker.Mock(params={}, spec=DootActionSpec)
        state         = {}
        result        = obj.to_path(spec, state)
        assert(isinstance(result, pl.Path))
        assert(result == pl.Path(target).expanduser().resolve())

    @pytest.mark.parametrize("name", MULTI_KEYS + NON_PATH_MUTI_KEYS)
    def test_set_default_expansion(self, name):
        spec  = DootActionSpec(kwargs=TomlGuard({"x": "aweg", "y_": "a"}))
        state = {"a": "bloo", "b_": "blee"}
        obj   = dkey.DootKey.build(name, strict=False)
        obj.set_expansion_hint("str")
        assert(isinstance(obj(spec, state), str))

class TestKeySimple:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec(kwargs=TomlGuard({"x": "aweg", "y_": "a"}))

    @pytest.fixture(scope="function")
    def state(self):
        return {"a": "bloo", "b_": "blee"}

    def test_basic_expand(self):
        example = DootKey.build("blah")
        assert(isinstance(example, str))
        assert(isinstance(example, DootKey))

    def test_eq(self):
        example = DootKey.build("blah")
        other   = DootKey.build("blah")
        assert(example == other)
        assert(example == example)
        assert(example is example)
        assert(example is not other)
        assert(example == "blah")

    def test_contains(self):
        example = DootKey.build("blah")
        assert(example in "this is a {blah} test")
        assert("blah" in example)

    def test_contain_fail(self):
        example = DootKey.build("blah")
        assert(example.form not in "this is a blah test")
        assert(example not in "this is a {bloo} test")
        assert("bloo" not in example)

    def test_within(self):
        example = DootKey.build("blah")
        assert(example.within("this is a {blah} test"))

    def test_within_fail(self):
        example = DootKey.build("blah")
        assert(not example.within("this is a blah test"))

    def test_within_dict(self):
        example = DootKey.build("blah")
        assert(example.within({"blah": "aweg"}))

    def test_within_dict_fail(self):
        example = DootKey.build("blah")
        assert(not example.within({"bloo": "aweg"}))
        assert(not example.within({"{bloo}": "aweg"}))

    def test_str_call(self):
        example = DootKey.build("blah")
        assert(str(example) == "blah")

    def test_form(self):
        example = DootKey.build("blah")
        assert(example.form == "{blah}")

    def test_repr_call(self):
        example = DootKey.build("blah")
        assert(repr(example) == "<DootSimpleKey: blah>")

    def test_indirect(self):
        example = DootKey.build("blah")
        assert(example.indirect == "blah_")

    def test_expand_nop(self, spec, state):
        example = DootKey.build("blah")
        result = example.expand(spec, state)
        assert(result == "{blah}")

    def test_expand(self, spec, state):
        example       = DootKey.build("x")
        result        = example.expand(spec, state)
        assert(result == "aweg")

    def test_format_nested(self, spec, state):
        example = DootKey.build("c")
        state['c'] = DootKey.build("a")
        result = example.expand(spec, state)
        assert(result == "bloo")

    def test_in_dict(self, spec, state):
        example = DootKey.build("c")
        the_dict = {example : "blah"}
        assert(example in the_dict)

    def test_equiv_in_dict(self, spec, state):
        example = DootKey.build("c")
        the_dict = {"c": "blah"}
        assert(example in the_dict)
