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
from doot._structs.action_spec import ActionSpec
from doot._structs import dkey as dkey
from doot.utils.dkey_formatter import DKeyFormatter

KEY_BASES               : Final[str]           = ["bob", "bill", "blah", "other"]
WRAPPED_KEY_BASES       : Final[str]           = ["{bob}", "{bill}", "{blah}", "{other}"]
PARAM_KEY_BASES         : Final[str]           = ["{bob:wd}", "{bill:w}", "{blah:wi}", "{other:i}"]
MULTI_KEYS              : Final[str]           = ["{bob}/{bill}", "{blah}/{bloo}", "{blah}/{bloo}"]
NON_PATH_MUTI_KEYS      : Final[str]           = ["{bob}_{bill}", "{blah} <> {bloo}", "! {blah}! {bloo}!"]
KEY_INDIRECTS           : Final[str]           = ["bob_", "bill_", "blah_", "other_"]
WRAPPED_KEY_INDIRECTS           : Final[str]           = ["bob_", "bill_", "blah_", "other_"]

VALID_KEYS       = KEY_BASES + WRAPPED_KEY_BASES + PARAM_KEY_BASES + KEY_INDIRECTS + WRAPPED_KEY_INDIRECTS
VALID_MULTI_KEYS = MULTI_KEYS + NON_PATH_MUTI_KEYS

TEST_LOCS               : Final[DootLocations] = DootLocations(pl.Path.cwd()).update({"blah": "doot"})

class TestDKeyConstruction:

    @pytest.mark.parametrize("name", VALID_KEYS)
    def test_base_key(self, name):
        obj = dkey.SimpleDKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))
        assert("{" not in obj)
        assert(hasattr(obj, "_fparams"))

    @pytest.mark.parametrize("name", VALID_KEYS)
    def test_build(self, name):
        obj = dkey.DKey.build(name)
        assert(isinstance(obj, dkey.DKey))

    @pytest.mark.parametrize("name", WRAPPED_KEY_BASES)
    def test_build_from_wrapped(self, name):
        obj = dkey.DKey.build(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.SimpleDKey))
        assert("{" not in obj)

    @pytest.mark.parametrize("name", PARAM_KEY_BASES)
    def test_build_with_params(self, name):
        obj = dkey.SimpleDKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_key_str(self, name):
        obj = dkey.SimpleDKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))
        assert(str(obj) == name)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_key_down_to_str(self, name):
        obj = dkey.SimpleDKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))
        as_str = str(obj)
        assert(as_str == name)
        assert(not isinstance(as_str, dkey.DKey))
        assert(isinstance(as_str, str))

    @pytest.mark.parametrize("name", MULTI_KEYS)
    def test_keys_error_on_multi_keys(self, name):
        with pytest.raises(ValueError):
            dkey.SimpleDKey(name)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_build_explicit_(self, name):
        explicit = "".join(["{", name, "}"])
        obj = dkey.DKey.build(explicit, explicit=True)
        assert(isinstance(obj, dkey.DKey))
        assert(str(obj) == name)

    @pytest.mark.parametrize("name", MULTI_KEYS + NON_PATH_MUTI_KEYS)
    def test_multi_build(self, name):
        obj = dkey.DKey.build(name)
        assert(isinstance(obj, dkey.DKey))
        assert(not isinstance(obj, dkey.SimpleDKey))
        assert(isinstance(obj, dkey.MultiDKey))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_build_idempotent(self, name):
        obj1 = dkey.DKey.build(name)
        obj2 = dkey.DKey.build(obj1)
        assert(isinstance(obj1, dkey.DKey))
        assert(isinstance(obj2, dkey.DKey))
        assert(obj1 == obj2)
        assert(obj1 is obj2)
        assert(id(obj1) == id(obj2))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_build_non_key(self, name):
        obj = dkey.DKey.build(name, explicit=True)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.NonDKey))

    @pytest.mark.parametrize("name", KEY_INDIRECTS)
    def test_build_indirect(self, name):
        obj = dkey.DKey.build(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.SimpleDKey))
        assert(str(obj) == name)

class TestDKeyDunderFormatting:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "bloo", "a": 2}))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_initial_fstr(self, spec, name):
        """ key -> key"""
        key           = dkey.DKey.build(name)
        result        = f"{key}"
        assert(result == name)

    @pytest.mark.parametrize("name", KEY_INDIRECTS)
    def test_fstr_indirect(self, spec, name):
        """ keys_ -> keys_"""
        key           = dkey.DKey.build(name)
        result        = f"{key}"
        assert(result == name)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_fstr_wrapped(self, spec, name):
        """ key -> {key} """
        key           = dkey.DKey.build(name)
        result        = f"{key:w}"
        assert(result == "".join(["{", name, "}"]))

    @pytest.mark.parametrize("name", KEY_INDIRECTS)
    def test_fstr_wrapped_indirect(self, spec, name):
        """ keys_ -> {keys_}"""
        key           = dkey.DKey.build(name)
        result        = f"{key:w}"
        assert(result == "".join(["{", name, "}"]))

    @pytest.mark.parametrize("name", KEY_BASES + KEY_INDIRECTS)
    def test_coerce_direct_to_wrapped_indirect(self, spec, name):
        """ {key} -> {key_} """
        key           = dkey.DKey.build(name)
        result        = f"{key:wi}"
        assert(result == "".join(["{", name.removesuffix("_"), "_", "}"]))

    @pytest.mark.parametrize("name", KEY_BASES + KEY_INDIRECTS)
    def test_coerce_indirect_to_wrapped_direct(self, spec, name):
        """ {key_} -> {key} """
        key           = dkey.DKey.build(name)
        result        = f"{key:wd}"
        assert(result == "".join(["{", name.removesuffix("_"), "}"]))

    @pytest.mark.parametrize("name", MULTI_KEYS)
    def test_fstr_multi_key(self, spec, name):
        """ multi keys are explicit by default """
        key           = dkey.DKey.build(name)
        result        = f"{key}"
        assert(result == name)
        assert(bool(key.keys()))

    @pytest.mark.parametrize("name", MULTI_KEYS)
    def test_fstr_multi_explicit(self, spec, name):
        """ specifying alt form does nothing """
        key           = dkey.DKey.build(name)
        explicit = f"{key:w}"
        implicit = f"{key:i}"
        assert(explicit == name == implicit)
        assert(bool(key.keys()))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_fstr_non_key(self, spec, name):
        """ non keys cant be explicit, specifying alt form does nothing """
        key           = dkey.DKey.build(name, explicit=True)
        assert(isinstance(key, dkey.NonDKey))
        explicit = f"{key:w}"
        implicit = f"{key}"
        assert(explicit == name == implicit)


    def test_str_format(self):
        key = dkey.SimpleDKey("x")
        result = "{}".format(key)
        assert(result == "x")

    def test_fstr_format(self):
        key = dkey.SimpleDKey("x")
        result = f"{key}"
        assert(result == "x")

    def test_fstr_with_width(self):
        key = dkey.SimpleDKey("x")
        result = f"{key: <5w}"
        assert(result == "{x}  ")

    def test_nonkey_format(self):
        fmt = DKeyFormatter()
        key = dkey.NonDKey("x")
        result = fmt.format(key)
        assert(result == "x")

class TestDKeyExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "a", "a": 2}))

    def test_initial(self):
        key = dkey.DKey.build("x")
        assert(isinstance(key, dkey.DKey))

    def test_simple_expansion(self, spec):
        key = dkey.DKey.build("a")
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec)
        assert(isinstance(result, int))
        assert(result == 2)

    def test_type_coerce_expansion(self, spec):
        key = dkey.DKey.build("a", ehint=float)
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec)
        assert(isinstance(result, float))
        assert(result == 2)

    def test_indirect_recursive_expansion(self, spec):
        key = dkey.DKey.build("z")
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec)
        assert(result == 2)

    def test_state_expansion(self, spec):
        key = dkey.DKey.build("blah")
        state = {"blah": "bloo"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(result == "bloo")

    def test_missing_expansion(self, spec):
        key = dkey.DKey.build("blah")
        state = {}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(result == None)

    def test_explicit_expansion(self, spec):
        key = dkey.DKey.build("{blah}")
        state = {"blah": "bloo"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(result == "bloo")

    def test_direct_when_no_indirect(self, spec):
        key = dkey.DKey.build("{blah_}")
        state = {"blah": "bloo"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(result == "bloo")

    def test_multikey_str_expansion(self, spec):
        key = dkey.DKey.build("{blah} {bloo}", ehint=str)
        state = {"blah": "aweg", "bloo": "gawe"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(result == "aweg gawe")

    def test_multikey_missing_expansion(self, spec):
        key = dkey.DKey.build("{blah} {bloo}")
        state = {"blah": "aweg"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(result == "aweg {bloo}")

    def test_multikey_expansion_to_path(self, spec):
        key = dkey.DKey.build("{blah}/{bloo}", ehint=pl.Path)
        assert(isinstance(key, dkey.MultiDKey))
        assert(key._etype is pl.Path)
        state = {"blah": pl.Path("aweg"), "bloo":"wegg"}
        result = key.expand(spec=spec, state=state)
        assert(isinstance(result, pl.Path))
        assert(result == doot.locs[pl.Path("aweg/wegg")])

    def test_nested_expansion(self, spec):
        key = dkey.DKey.build("top")
        assert(isinstance(key, dkey.DKey))
        state = {"top": dkey.DKey.build("{y} : {a}")}
        result = key.expand(spec=spec, state=state)
        assert(result == "aweg : 2")


    def test_recursive_expansion(self, spec):
        key = dkey.DKey.build("top")
        assert(isinstance(key, dkey.DKey))
        state = {"top_": "b", "b": dkey.DKey.build("{b}")}
        result = key.expand(spec=spec, state=state)
        assert(result == "{b}")


    def test_typed_expansion(self, spec):
        state = {"test": set([1,2,3,4])}
        key   = dkey.DKey.build("test")
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(isinstance(result, set))

@pytest.mark.skip
class TestKeyParameterized:

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_eq(self, name):
        obj = dkey.SimpleDKey(name)
        assert(obj == name)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_form(self, name):
        obj = dkey.SimpleDKey(name)
        assert(obj.form.startswith("{"))
        assert(obj.form.endswith("}"))

    @pytest.mark.parametrize("name,target,within", [("bob", "{bob}", True), ("bob", "bob", False)])
    def test_within(self, name, target, within):
        obj = dkey.SimpleDKey(name)
        assert(obj.within(target) == within)

    @pytest.mark.parametrize("name", KEY_INDIRECTS)
    def test_is_indirect(self, name):
        obj = dkey.SimpleDKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(obj.is_indirect)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_not_is_indirect(self, name):
        obj = dkey.SimpleDKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(not obj.is_indirect)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_hash(self, name):
        obj = dkey.SimpleDKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(hash(name) == hash(name))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_indirect(self, name):
        obj = dkey.SimpleDKey(name)
        assert(not obj.indirect.endswith("__"))

    @pytest.mark.parametrize("name", KEY_INDIRECTS)
    def test_indirect_idempotent(self, name):
        assert(name.endswith("_"))
        obj = dkey.SimpleDKey(name)
        assert(not obj.indirect.endswith("__"))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_redirect(self, mocker, name):
        obj           = dkey.SimpleDKey(name)
        spec          = mocker.Mock(params={f"{name}_": "blah"}, spec=ActionSpec)
        assert(obj.indirect in spec.params)
        result        = obj.redirect(spec)
        assert(isinstance(result, dkey.DKey))
        assert(result == "blah")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_redirect_to_list_fail(self, mocker, name):
        obj           = dkey.SimpleDKey(name)
        spec          = mocker.Mock(params={f"{name}_": ["blah", "bloo"]}, spec=ActionSpec)
        assert(obj.indirect in spec.params)
        with pytest.raises(TypeError):
            result        = obj.redirect(spec)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_redirect_multi(self, mocker, name):
        obj           = dkey.SimpleDKey(name)
        spec          = mocker.Mock(params={f"{name}_": ["blah", "bloo"]}, spec=ActionSpec)
        assert(obj.indirect in spec.params)
        result        = obj.redirect_multi(spec)
        assert(isinstance(result, list))
        assert(all((isinstance(x, dkey.DKey) for x in result)))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expand_from_spec(self, mocker, name):
        obj           = dkey.SimpleDKey(name)
        spec          = mocker.Mock(params={f"{obj}": "blah"}, spec=ActionSpec)
        result        = obj.expand(spec, {})
        assert(result == "blah")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expand_from_state(self, mocker, name):
        obj           = dkey.SimpleDKey(name)
        spec          = mocker.Mock(params={}, spec=ActionSpec)
        state         = {f"{obj}": "blah"}
        result        = obj.expand(spec, state)
        assert(result == "blah")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expansion_prefers_spec_over_state(self, mocker, name):
        obj           = dkey.SimpleDKey(name)
        spec          = mocker.Mock(params={f"{obj}": "bloo"}, spec=ActionSpec)
        state         = {f"{obj}": "blah"}
        result        = obj.expand(spec, state)
        assert(result == "bloo")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expansion_prefers_redirect_over_other(self, mocker, name):
        obj           = dkey.SimpleDKey(name)
        spec          = mocker.Mock(params={"aweg": "bloo", obj.indirect : "aweg"}, spec=ActionSpec)
        state         = {f"{obj}": "blah"}
        result        = obj.expand(spec, state)
        assert(result == "bloo")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_expansion_of_missing_returns_form(self, mocker, name):
        obj           = dkey.SimpleDKey(name)
        spec          = mocker.Mock(params={}, spec=ActionSpec)
        state         = {}
        result        = obj.expand(spec, state)
        assert(result == obj.form)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_recursive_expansion(self, mocker, name):
        obj           = dkey.SimpleDKey(name)
        spec          = mocker.Mock(params={f"{name}": dkey.SimpleDKey("key1")}, spec=ActionSpec)
        state         = {"key1": dkey.SimpleDKey("key2"), "key2": "aweg"}
        result        = obj.expand(spec, state)
        assert(result == "aweg")

    @pytest.mark.parametrize("name", KEY_BASES)
    @pytest.mark.parametrize("value,type", [([1,2,3], list)])
    def test_expansion_flattening(self, mocker, name, value, type):
        obj           = dkey.SimpleDKey(name)
        spec          = mocker.Mock(params={}, spec=ActionSpec)
        state         = {name: value}
        result        = obj.expand(spec, state)
        assert(isinstance(result, str))
        assert(result == str(value))

    @pytest.mark.parametrize("name", KEY_BASES)
    @pytest.mark.parametrize("value,type", [([1,2,3], list)])
    def test_to_type_expansion(self, mocker, name, value, type):
        obj           = dkey.SimpleDKey(name)
        spec          = mocker.Mock(params={}, spec=ActionSpec)
        state         = {name: value}
        result        = obj.to_type(spec, state)
        assert(isinstance(result, type))
        assert(result == value)

    @pytest.mark.parametrize("name", KEY_BASES)
    @pytest.mark.parametrize("value,type", [([1,2,3], list)])
    def test_to_type_on_fail(self, mocker, name, value, type):
        obj           = dkey.SimpleDKey(name)
        spec          = mocker.Mock(params={}, spec=ActionSpec)
        state         = {}
        result        = obj.to_type(spec, state, on_fail="blah")
        # assert(isinstance(result, type))
        assert(result == "blah")

    @pytest.mark.parametrize("name", KEY_BASES)
    @pytest.mark.parametrize("value,type", [([1,2,3], list)])
    def test_to_type_on_fail_nop(self, mocker, name, value, type):
        obj           = dkey.SimpleDKey(name)
        spec          = mocker.Mock(params={}, spec=ActionSpec)
        state         = {name : value}
        result        = obj.to_type(spec, state, on_fail="blah")
        # assert(isinstance(result, type))
        assert(result == value)

    @pytest.mark.parametrize("key,target", [("blah", "./doot")])
    def test_to_path_expansion(self, mocker, key, target):
        mocker.patch.dict("doot.__dict__", locs=TEST_LOCS)
        obj           = dkey.DKey.build(key)
        spec          = mocker.Mock(params={}, spec=ActionSpec)
        state         = {}
        result        = obj.to_path(spec, state)
        assert(isinstance(result, pl.Path))
        assert(result == pl.Path(target).expanduser().resolve())

    @pytest.mark.parametrize("name", MULTI_KEYS + NON_PATH_MUTI_KEYS)
    def test_set_default_expansion(self, name):
        spec  = ActionSpec(kwargs=TomlGuard({"x": "aweg", "y_": "a"}))
        state = {"a": "bloo", "b_": "blee"}
        obj   = dkey.dkey.DKey.build(name, strict=False)
        obj.set_expansion_hint("str")
        assert(isinstance(obj(spec, state), str))

@pytest.mark.skip
class TestKeySimple:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"x": "aweg", "y_": "a"}))

    @pytest.fixture(scope="function")
    def state(self):
        return {"a": "bloo", "b_": "blee"}

    def test_basic_expand(self):
        example = dkey.DKey.build("blah")
        assert(isinstance(example, str))
        assert(isinstance(example, dkey.DKey))

    def test_eq(self):
        example = dkey.DKey.build("blah")
        other   = dkey.DKey.build("blah")
        assert(example == other)
        assert(example == example)
        assert(example is example)
        assert(example is not other)
        assert(example == "blah")

    def test_contains(self):
        example = dkey.DKey.build("blah")
        assert(example in "this is a {blah} test")
        assert("blah" in example)

    def test_contain_fail(self):
        example = dkey.DKey.build("blah")
        assert(example.form not in "this is a blah test")
        assert(example not in "this is a {bloo} test")
        assert("bloo" not in example)

    def test_within(self):
        example = dkey.DKey.build("blah")
        assert(example.within("this is a {blah} test"))

    def test_within_fail(self):
        example = dkey.DKey.build("blah")
        assert(not example.within("this is a blah test"))

    def test_within_dict(self):
        example = dkey.DKey.build("blah")
        assert(example.within({"blah": "aweg"}))

    def test_within_dict_fail(self):
        example = dkey.DKey.build("blah")
        assert(not example.within({"bloo": "aweg"}))
        assert(not example.within({"{bloo}": "aweg"}))

    def test_str_call(self):
        example = dkey.DKey.build("blah")
        assert(str(example) == "blah")

    def test_form(self):
        example = dkey.DKey.build("blah")
        assert(example.form == "{blah}")

    def test_repr_call(self):
        example = dkey.DKey.build("blah")
        assert(repr(example) == "<SimpleDKey: blah>")

    def test_indirect(self):
        example = dkey.DKey.build("blah")
        assert(example.indirect == "blah_")

    def test_expand_nop(self, spec, state):
        example = dkey.DKey.build("blah")
        result = example.expand(spec, state)
        assert(result == "{blah}")

    def test_expand(self, spec, state):
        example       = dkey.DKey.build("x")
        result        = example.expand(spec, state)
        assert(result == "aweg")

    def test_format_nested(self, spec, state):
        example = dkey.DKey.build("c")
        state['c'] = dkey.DKey.build("a")
        result = example.expand(spec, state)
        assert(result == "bloo")

    def test_in_dict(self, spec, state):
        example = dkey.DKey.build("c")
        the_dict = {example : "blah"}
        assert(example in the_dict)

    def test_equiv_in_dict(self, spec, state):
        example = dkey.DKey.build("c")
        the_dict = {"c": "blah"}
        assert(example in the_dict)
