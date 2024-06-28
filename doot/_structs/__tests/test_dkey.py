#!/usr/bin/env python4
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
from doot._structs.code_ref import CodeReference
from doot._abstract.protocols import Key_p

KEY_BASES               : Final[str]           = ["bob", "bill", "blah", "other", "23boo", "aweg2531", "awe_weg", "aweg-weji-joi"]
WRAPPED_KEY_BASES       : Final[str]           = [f"{{{x}}}" for x in KEY_BASES]
PARAM_KEY_BASES         : Final[str]           = ["{bob:wd}", "{bill:w}", "{blah:wi}", "{other:i}"]
MULTI_KEYS              : Final[str]           = ["{bob}/{bill}", "{blah}/{bloo}", "{blah}/{bloo}"]
NON_PATH_MUTI_KEYS      : Final[str]           = ["{bob}_{bill}", "{blah} <> {bloo}", "! {blah}! {bloo}!"]
KEY_INDIRECTS           : Final[str]           = ["bob_", "bill_", "blah_", "other_"]
WRAPPED_KEY_INDIRECTS           : Final[str]           = ["bob_", "bill_", "blah_", "other_"]

VALID_KEYS       = KEY_BASES + WRAPPED_KEY_BASES + PARAM_KEY_BASES + KEY_INDIRECTS + WRAPPED_KEY_INDIRECTS
VALID_MULTI_KEYS = MULTI_KEYS + NON_PATH_MUTI_KEYS

TEST_LOCS               : Final[DootLocations] = DootLocations(pl.Path.cwd()).update({"blah": "doot"})

class TestDKeyConstruction:

    def test_initial(self):
        key  = dkey.DKey("{test}")
        assert(isinstance(key, dkey.SingleDKey))
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, str))
        assert(isinstance(key, Key_p))
        assert(f"{key:w}" == "{test}")
        assert(f"{key:i}" == "test_")
        assert(str(key) == "test")

    def test_subclass_check(self):
        assert(issubclass(dkey.SingleDKey, dkey.DKey))

    def test_initial_no_wrap(self):
        key  = dkey.DKey("test")
        assert(isinstance(key, dkey.SingleDKey))
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, str))
        assert(f"{key:w}" == "{test}")
        assert(f"{key:i}" == "test_")
        assert(str(key) == "test")

    def test_simple_with_fparams(self):
        key  = dkey.DKey("{test:w}")
        assert(isinstance(key, dkey.SingleDKey))
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, str))
        assert(key._fparams == "w")

    def test_initial_mkey(self):
        key  = dkey.DKey("{test}/{blah}")
        assert(isinstance(key, dkey.MultiDKey))
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, str))
        assert(key._fparams == None)
        assert(key.keys() == [dkey.DKey("test"), dkey.DKey("blah")])

    def test_initial_nonkey(self):
        key  = dkey.DKey("blah bloo blee", explicit=True)
        assert(isinstance(key, dkey.NonDKey))
        assert(isinstance(key, str))
        assert(isinstance(key, dkey.DKey))

    def test_init_with_fparams(self):
        key  = dkey.DKey("{test:w}")
        assert(isinstance(key, dkey.SingleDKey))
        assert(key._fparams == "w")

    def test_subclass_creation_fail(self):
        with pytest.raises(RuntimeError):
            dkey.SingleDKey("test")

    def test_subclass_creation_force(self):
        key = dkey.SingleDKey("test", force=True)
        assert(key is not None)
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, dkey.SingleDKey))

    @pytest.mark.parametrize("name", VALID_KEYS)
    def test_base_key(self, name):
        obj = dkey.DKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))
        assert("{" not in obj)
        assert(hasattr(obj, "_fparams"))

    @pytest.mark.skip
    @pytest.mark.parametrize("name", ["{bob:p}/{bill}"])
    def test_build_path_key_from_str(self, name):
        obj = dkey.DKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))
        assert(obj._etype is pl.Path)

    @pytest.mark.parametrize("name", VALID_KEYS)
    @pytest.mark.parametrize("check", [int,str,int|float,list[int],list[str|float], Any, None])
    def test_build_with_typecheck(self, name, check):
        obj = dkey.DKey(name, check=check)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))
        assert(obj._typecheck == check or Any)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_key_str(self, name):
        obj = dkey.DKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))
        assert(str(obj) == name)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_key_down_to_str(self, name):
        obj = dkey.DKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))
        as_str = str(obj)
        assert(as_str == name)
        assert(not isinstance(as_str, dkey.DKey))
        assert(isinstance(as_str, str))

    @pytest.mark.xfail
    @pytest.mark.parametrize("name", MULTI_KEYS)
    def test_keys_error_on_multi_keys(self, name):
        with pytest.raises(ValueError):
            dkey.SingleDKey(name)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_build_explicit_(self, name):
        explicit = "".join(["{", name, "}"])
        obj = dkey.DKey(explicit, explicit=True)
        assert(isinstance(obj, dkey.DKey))
        assert(str(obj) == name)

    @pytest.mark.parametrize("name", MULTI_KEYS + NON_PATH_MUTI_KEYS)
    def test_multi_build(self, name):
        obj = dkey.DKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(not isinstance(obj, dkey.SingleDKey))
        assert(isinstance(obj, dkey.MultiDKey))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_build_idempotent(self, name):
        obj1 = dkey.DKey(name)
        obj2 = dkey.DKey(obj1)
        assert(isinstance(obj1, dkey.DKey))
        assert(isinstance(obj2, dkey.DKey))
        assert(obj1 == obj2)
        assert(obj1 is obj2)
        assert(id(obj1) == id(obj2))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_build_non_key(self, name):
        obj = dkey.DKey(name, explicit=True)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.NonDKey))

    @pytest.mark.parametrize("name", KEY_INDIRECTS)
    def test_build_indirect(self, name):
        obj = dkey.DKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.SingleDKey))
        assert(str(obj) == name)

class TestDKeyDunderFormatting:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "bloo", "a": 2}))


    @pytest.mark.parametrize("name", KEY_BASES)
    def test_repr(self, name):
        key = dkey.DKey(name)
        assert(repr(key) == f"<SingleDKey: {key}>")


    @pytest.mark.parametrize("name", MULTI_KEYS)
    def test_multi_repr(self, name):
        key = dkey.DKey(name)
        assert(repr(key) == f"<MultiDKey: {key}>")


    @pytest.mark.parametrize("name", KEY_BASES)
    def test_initial_fstr(self, spec, name):
        """ key -> key"""
        key           = dkey.DKey(name)
        result        = f"{key}"
        assert(result == name)

    @pytest.mark.parametrize("name", KEY_INDIRECTS)
    def test_fstr_indirect(self, spec, name):
        """ keys_ -> keys_"""
        key           = dkey.DKey(name)
        result        = f"{key}"
        assert(result == name)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_fstr_wrapped(self, spec, name):
        """ key -> {key} """
        key           = dkey.DKey(name)
        result        = f"{key:w}"
        assert(result == "".join(["{", name, "}"]))

    @pytest.mark.parametrize("name", KEY_INDIRECTS)
    def test_fstr_wrapped_indirect(self, spec, name):
        """ keys_ -> {keys_}"""
        key           = dkey.DKey(name)
        result        = f"{key:wi}"
        assert(result == "".join(["{", name, "}"]))

    @pytest.mark.parametrize("name", KEY_BASES + KEY_INDIRECTS)
    def test_coerce_direct_to_wrapped_indirect(self, spec, name):
        """ {key} -> {key_} """
        key           = dkey.DKey(name)
        result        = f"{key:wi}"
        assert(result == "".join(["{", name.removesuffix("_"), "_", "}"]))

    @pytest.mark.parametrize("name", KEY_BASES + KEY_INDIRECTS)
    def test_coerce_indirect_to_wrapped_direct(self, spec, name):
        """ {key_} -> {key} """
        key           = dkey.DKey(name)
        result        = f"{key:wd}"
        assert(result == "".join(["{", name.removesuffix("_"), "}"]))

    @pytest.mark.parametrize("name", MULTI_KEYS)
    def test_fstr_multi_key(self, spec, name):
        """ multi keys are explicit by default """
        key           = dkey.DKey(name)
        result        = f"{key}"
        assert(result == name)
        assert(bool(key.keys()))

    @pytest.mark.parametrize("name", MULTI_KEYS)
    def test_fstr_multi_explicit(self, spec, name):
        """ specifying alt form does nothing """
        key           = dkey.DKey(name)
        explicit = f"{key:w}"
        implicit = f"{key:i}"
        assert(explicit == name == implicit)
        assert(bool(key.keys()))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_fstr_non_key(self, spec, name):
        """ non keys cant be explicit, specifying alt form does nothing """
        key           = dkey.DKey(name, explicit=True)
        assert(isinstance(key, dkey.NonDKey))
        explicit = f"{key:w}"
        implicit = f"{key}"
        assert(explicit == name == implicit)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_str_format(self, name):
        key = dkey.DKey(name)
        result = "{}".format(key)
        assert(result == name)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_fstr_format(self, name):
        key = dkey.DKey(name)
        result = f"{key}"
        assert(result == name)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_fstr_with_width(self, name):
        key = dkey.DKey(name)
        result = f"{key: <5}"
        assert(result == f"{name: <5}")

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_nonkey_format(self, name):
        key           = dkey.DKey(name, explicit=True)
        result        = f"{key}"
        assert(result == name)

    @pytest.mark.parametrize("name", MULTI_KEYS)
    def test_multikey_format(self, name):
        key    = dkey.DKey(name)
        result = f"{key}"
        assert(isinstance(key, dkey.MultiDKey))
        assert(result == name)

class TestDKeyComparison:

    @pytest.mark.parametrize("name", VALID_KEYS)
    def test_initial(self, name):
        key1 = dkey.DKey(name)
        key2 = dkey.DKey(name)
        assert(key1 == key2)
        assert(key1 is not key2)

    @pytest.mark.parametrize("name", VALID_KEYS)
    def test_hashing(self, name):
        key1 = dkey.DKey(name)
        key2 = dkey.DKey(name)
        assert(hash(key1) == hash(key2) == hash(str(key1)) == hash(str(key2)))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_key_and_str(self, name):
        """ both __and__ + __rand__ """
        key      = dkey.DKey(name)
        test_str = "this is a {} test".format(f"{key:w}")
        assert(key & test_str)
        assert(test_str & key)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_key_and_str_fail(self, name):
        """ both __and__ + __rand__ """
        key      = dkey.DKey(name)
        test_str = "this is a {} test".format(f"{key}")
        assert(not (key & test_str))
        assert(not (test_str & key))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_key_eq(self, name):
        """   """
        key      = dkey.DKey(name)
        assert( key == name )

class TestDKeyExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "a", "a": 2}))

    def test_initial(self):
        key = dkey.DKey("x")
        assert(isinstance(key, dkey.DKey))

    def test_simple_expansion(self, spec):
        """ a -> 2 """
        key = dkey.DKey("a")
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec)
        assert(isinstance(result, int))
        assert(result == 2)

    def test_type_coerce_expansion(self, spec):
        """ a -> 2 (float) """
        key = dkey.DKey("a", ehint=float)
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec)
        assert(isinstance(result, float))
        assert(result == 2)

    def test_indirect_recursive_expansion(self, spec):
        """ z -> z_ -> a -> 2 """
        key = dkey.DKey("z")
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec)
        assert(result == 2)

    def test_state_expansion(self, spec):
        """ blah -> bloo """
        key = dkey.DKey("blah")
        state = {"blah": "bloo"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(result == "bloo")

    def test_missing_expansion(self, spec):
        """ blah -> None """
        key = dkey.DKey("blah")
        state = {}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(result == None)

    def test_explicit_expansion(self, spec):
        """
          blah -> bloo
        """
        key = dkey.DKey("{blah}")
        state = {"blah": "bloo"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(result == "bloo")

    def test_direct_when_no_indirect(self, spec):
        """
          blah_ -> blah -> bloo
        """
        key = dkey.DKey("{blah_}")
        state = {"blah": "bloo"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(result == "bloo")

    def test_multikey_str_expansion(self, spec):
        """
          blah -> aweg
          bloo -> gawe
        """
        key = dkey.DKey("{blah} {bloo}", ehint=str)
        state = {"blah": "aweg", "bloo": "gawe"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(result == "aweg gawe")

    def test_multikey_missing_expansion(self, spec):
        """
          blah -> aweg
          bloo -> {bloo}
        """
        key = dkey.DKey("{blah} {bloo}")
        state = {"blah": "aweg"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(result == "aweg {bloo}")

    def test_multikey_expansion_to_path(self, spec):
        """
          blah/bloo -> aweg/wegg
        """
        key = dkey.DKey("{blah}/{bloo}", ehint=pl.Path)
        assert(isinstance(key, dkey.MultiDKey))
        assert(key._etype is pl.Path)
        state = {"blah": pl.Path("aweg"), "bloo":"wegg"}
        result = key.expand(spec=spec, state=state)
        assert(isinstance(result, pl.Path))
        assert(result == doot.locs[pl.Path("aweg/wegg")])

    def test_nested_expansion(self, spec):
        """
          top -> {y} : {a} -> aweg : 2
        """
        key = dkey.DKey("top")
        assert(isinstance(key, dkey.DKey))
        state = {"top": dkey.DKey("{y} : {a}")}
        result = key.expand(spec=spec, state=state)
        assert(result == "aweg : 2")

    def test_recursive_expansion(self, spec):
        """
          top -> b -> {b}
        """
        key = dkey.DKey("top")
        assert(isinstance(key, dkey.DKey))
        state = {"top_": "b", "b": dkey.DKey("{b}")}
        result = key.expand(spec=spec, state=state)
        assert(result == "{b}")

    def test_typed_expansion(self, spec):
        """
          test -> {1,2,3,4}
        """
        state = {"test": set([1,2,3,4])}
        key   = dkey.DKey("test")
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(isinstance(result, set))

    def test_expansion_with_check(self, spec):
        """
          test -> {1,2,3,4}
        """
        state = {"test": set([1,2,3,4])}
        key   = dkey.DKey("test", check=set[int])
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(isinstance(result, set))

    def test_expansion_with_failed_check(self, spec):
        """
          test -> TypeError
        """
        state = {"test": [1,2,3,4]}
        key   = dkey.DKey("test", check=set[int])
        with pytest.raises(TypeError):
            key.expand(spec=spec, state=state)

    def test_expansion_with_failed_value_check(self, spec):
        """
          test -> TypeError
        """
        state = {"test": ["a","b","c","d"]}
        key   = dkey.DKey("test", check=list[int])
        with pytest.raises(TypeError):
            key.expand(spec=spec, state=state)

    def test_coderef_expansion(self, spec):
        """
          test -> coderef
        """
        state = {"test": "doot._structs.task_spec:TaskSpec"}
        key   = dkey.DKey("test", ehint=CodeReference)
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec=spec, state=state)
        assert(isinstance(result, CodeReference))

class TestDKeyFormatting:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "a", "a": 2}))

    def test_initial(self):
        key = dkey.DKey("x")
        fmt = DKeyFormatter()
        result = fmt.format(key)
