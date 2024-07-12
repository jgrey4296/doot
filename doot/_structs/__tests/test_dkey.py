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
from doot.structs import TaskName

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

    def test_sanity(self):
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
        assert(key._fparams is None)
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
        assert(obj._exp_type is pl.Path)

    @pytest.mark.parametrize("name", VALID_KEYS)
    @pytest.mark.parametrize("check", [int,str,int|float,list[int],list[str|float], Any, None])
    def test_build_with_typecheck(self, name, check):
        obj = dkey.DKey(name, check=check)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))
        assert(obj._typecheck == check or Any)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_key_str(self, name):
        """ keys are subclasses of str """
        obj = dkey.DKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))
        assert(str(obj) == name)

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_key_down_to_str(self, name):
        """ converting a key to a str removes its key-ness """
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
        """
          explicit single keys have their braces removed
        """
        explicit = "".join(["{", name, "}"])
        obj = dkey.DKey(explicit, explicit=True)
        assert(isinstance(obj, dkey.DKey))
        assert(str(obj) == explicit)

    @pytest.mark.parametrize("name", MULTI_KEYS + NON_PATH_MUTI_KEYS)
    def test_multi_build(self, name):
        """
          Keys with multiple expansion points are built as multi keys
        """
        obj = dkey.DKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(not isinstance(obj, dkey.SingleDKey))
        assert(isinstance(obj, dkey.MultiDKey))

    @pytest.mark.parametrize("name", KEY_BASES)
    def test_build_idempotent(self, name):
        """
          making a key from a key does nothing.
        """
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
        assert(isinstance(obj, dkey.RedirectionDKey))
        assert(str(obj) == name)

    def test_integrated_str_keys(self):
        obj = dkey.DKey("--{raise}", explicit=True)
        assert(str(obj) == "--{raise}")

    def test_conv_params_path(self):
        obj = dkey.DKey("{aval!p}")
        assert(isinstance(obj, dkey.PathSingleDKey))

    def test_conv_params_multi_path(self):
        obj = dkey.DKey("{aval!p}/{blah}")
        assert(isinstance(obj, dkey.MultiDKey))

    def test_conv_parms_redirect(self):
        obj = dkey.DKey("{aval!R}")
        assert(isinstance(obj, dkey.RedirectionDKey))

    def test_conv_params_code(self):
        obj = dkey.DKey("{aval!c}")
        assert(isinstance(obj, dkey.ImportDKey))

    def test_conv_parms_taskname(self):
        obj = dkey.DKey("{aval!t}")
        assert(isinstance(obj, dkey.TaskNameDKey))

    def test_conv_params_conflict(self):
        with pytest.raises(ValueError):
            dkey.DKey("{aval!p}", mark=dkey.DKey.mark.CODE)

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
    def test_sanity(self, name):
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

    def test_sanity(self):
        key = dkey.DKey("x")
        assert(isinstance(key, dkey.DKey))

    def test_simple_expansion(self, spec):
        """ a -> 2 """
        key = dkey.DKey("a")
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, dkey.SingleDKey))
        result = key.expand(spec)
        assert(isinstance(result, int))
        assert(result == 2)


    def test_simple_str_expansion(self):
        """ this is a {test} -> this is a blah """
        key = dkey.DKey("this is a {test}", explicit=True, mark=dkey.DKey.mark.STR)
        state = {"test": "blah"}
        result = key.expand(state)
        assert(isinstance(result, str))
        assert(result == "this is a blah")


    @pytest.mark.xfail
    def test_simple_indirect_str_expansion(self):
        """ a -> this is a {test} -> this is a blah """
        key = dkey.DKey("target", mark=dkey.DKey.mark.STR)
        state = {"test": "blah", "target" : "this is a {test!p}"}
        result = key.expand(state)
        assert(isinstance(result, str))
        assert(result == "this is a {}".format(doot.locs.normalize(pl.Path("blah"))))

    def test_state_expansion(self, spec):
        """ blah -> bloo """
        key = dkey.DKey("blah")
        state = {"blah": "bloo"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec, state)
        assert(result == "bloo")

    def test_missing_expansion(self, spec):
        """ blah -> None """
        key = dkey.DKey("blah")
        state = {}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec, state)
        assert(result is None)

    def test_missing_expansion_with_fallback(self, spec):
        """ blah -> None """
        key = dkey.DKey("blah", fallback="2345")
        state = {}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec, state)
        assert(result == "2345")

    def test_explicit_expansion(self, spec):
        """
          blah -> bloo
        """
        key = dkey.DKey("{blah}")
        state = {"blah": "bloo"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec, state)
        assert(result == "bloo")

    def test_recursive_expansion_literal_key(self, spec):
        """
          top -> b -> {b}
        """
        key = dkey.DKey("top")
        assert(isinstance(key, dkey.DKey))
        state = {"top_": "b", "b": dkey.DKey("{b}")}
        result = key.expand(spec, state)
        assert(result == "b")
        assert(isinstance(result, dkey.DKey))

    @pytest.mark.xfail
    def test_recursive_expansion_str(self, spec):
        """
          top -> b -> {b}
        """
        key = dkey.DKey("top")
        assert(isinstance(key, dkey.DKey))
        state = {"top_": "b", "b": "{b}"}
        result = key.expand(spec, state)
        assert(result == "b")

    def test_expansion_with_none_sources(self, spec):
        """
          top -> b -> {b}
        """
        key = dkey.DKey("top", mark=dkey.DKey.mark.STR)
        assert(isinstance(key, dkey.DKey))
        state = {"top_": "b", "b": dkey.DKey("{b}")}
        result = key.expand(None, spec, state)
        assert(result == "{b}")

    def test_misc(self):
        key = dkey.DKey("simple", check=set|list)
        assert(key.expand({"simple": set([1,2,3,4])}) is not None)
        with pytest.raises(TypeError):
            key.expand({"simple": 2})
        assert(key.expand({}, fallback=set(["bob"])) == set(["bob"]))
        assert(key.expand() is None)

    def test_path_expansion_no_op(self):
        key = dkey.DKey(pl.Path("a/test"), explicit=True, mark=dkey.DKey.mark.PATH)
        assert(isinstance(key, dkey.PathMultiDKey))
        assert(key.expand() is not None)

    def test_expansion_explicit_key(self):
        key = dkey.DKey("--{raise}", explicit=True)
        result = key.expand({"raise":"minor"})
        assert(result == "--minor")

class TestDKeyMarkExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "a", "a": 2, "simple":"aweg"}))

    def test_mark_expansion(self, spec):
        """ a -> 2:str """
        key = dkey.DKey("a", mark=dkey.DKey.mark.STR)
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec)
        assert(isinstance(result, str))
        assert(result == "2")

    def test_mark_expansion_to_path(self, spec):
        """ simple -> aweg:pl.Path"""
        key = dkey.DKey("{simple}", mark=dkey.DKey.mark.PATH, explicit=True)
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, dkey.PathMultiDKey))
        result = key.expand(spec)
        assert(isinstance(result, pl.Path))
        assert(result == pl.Path("aweg").resolve())

    def test_mark_expansion_to_path_multi(self, spec):
        """ simple -> aweg:pl.Path"""
        key = dkey.DKey("{simple}/{a}", mark=dkey.DKey.mark.PATH)
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, dkey.PathMultiDKey))
        result = key.expand(spec)
        assert(isinstance(result, pl.Path))
        assert(result == pl.Path("aweg/2").resolve())

    def test_cwd_build(self):
        obj = dkey.DKey(".", mark=dkey.DKey.mark.PATH, explicit=True)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.PathMultiDKey))
        assert(obj.expand() == pl.Path.cwd())

    def test_coderef_expansion(self, spec):
        """
          test -> coderef
        """
        state = {"test": "doot._structs.task_spec:TaskSpec"}
        key   = dkey.DKey("test", mark=dkey.DKey.mark.CODE)
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec, state)
        assert(isinstance(result, CodeReference))

class TestDKeyExpansionTypeControl:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "a", "a": 2}))

    def test_type_coerce_expansion(self, spec):
        """ a -> 2 (float) """
        key = dkey.DKey("a", ctor=float)
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec)
        assert(isinstance(result, float))
        assert(result == 2.0)

    def test_expansion_with_check(self, spec):
        """
          test -> {1,2,3,4}
        """
        state = {"test": set([1,2,3,4])}
        key   = dkey.DKey("test", check=set[int])
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec, state)
        assert(isinstance(result, set))

    def test_expansion_with_failed_check(self, spec):
        """
          test -> TypeError
        """
        state = {"test": [1,2,3,4]}
        key   = dkey.DKey("test", check=set[int])
        with pytest.raises(TypeError):
            key.expand(spec, state)

    def test_expansion_with_failed_value_check(self, spec):
        """
          test -> TypeError
        """
        state = {"test": ["a","b","c","d"]}
        key   = dkey.DKey("test", check=list[int])
        with pytest.raises(TypeError):
            key.expand(spec, state)

    def test_typed_expansion(self, spec):
        """
          test -> {1,2,3,4}
        """
        state = {"test": set([1,2,3,4])}
        key   = dkey.DKey("test")
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec, state)
        assert(isinstance(result, set))

    @pytest.mark.xfail
    def test_expansion_with_type_spec_in_str(self, spec):
        """ check setting expansion parameters directly from the initial string
          {a!s} -> 2:str
          """
        key = dkey.DKey("{a!s}")
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec)
        assert(isinstance(result, str))
        assert(result == "2")

    def test_expansion_to_taskname(self):
        """
        test -> group::name
        """
        state = {"test": "group::name"}
        key = dkey.DKey("test", mark=dkey.DKey.mark.TASK)
        assert(isinstance(key, dkey.TaskNameDKey))
        result = key.expand(state)
        assert(isinstance(result, TaskName))

class TestDKeyExpansionIndirect:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "a", "a": 2}))

    def test_indirect_recursive_expansion(self, spec):
        """ z -> z_ -> a -> 2 """
        key = dkey.DKey("z")
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec)
        assert(result == 2)

    def test_indirect_recursive_to_str(self, spec):
        """ z -> z_ -> a -> 2 """
        key = dkey.DKey("{z}", mark=dkey.DKey.mark.STR)
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec)
        assert(result == "2")

    def test_direct_when_no_indirect(self, spec):
        """
          blah_ -> blah
        """
        key = dkey.DKey("{blah_}")
        state = {"blah": "bloo"}
        result = key.expand(state)
        assert(isinstance(result, dkey.DKey))
        assert(not isinstance(result, dkey.RedirectionDKey))
        assert(result == "blah")

    def test_nested_expansion(self, spec):
        """
          top -> {y} : {a} -> aweg : 2
        """
        key = dkey.DKey("top")
        assert(isinstance(key, dkey.DKey))
        state = {"top": dkey.DKey("{y} : {a}")}
        result = key.expand(spec, state)
        assert(result == "aweg : 2")

class TestDKeyMultiKeyExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "a", "a": 2}))

    def test_multikey_str_expansion(self, spec):
        """
          blah -> aweg
          bloo -> gawe
        """
        key = dkey.DKey("{blah} {bloo}", mark=dkey.DKey.mark.STR)
        state = {"blah": "aweg", "bloo": "gawe"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec, state)
        assert(result == "aweg gawe")

    def test_multikey_missing_expansion(self, spec):
        """
          blah -> aweg
          bloo -> {bloo}
        """
        key = dkey.DKey("{blah} {bloo}")
        state = {"blah": "aweg"}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec, state)
        assert(result == "aweg {bloo}")

    def test_multikey_with_nonstr_expansions(self, spec):
        """
          blah -> aweg
          bloo -> {bloo}
        """
        key = dkey.DKey("{blah} {bloo}")
        state = {"blah": "aweg", "bloo": 23}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(spec, state)
        assert(result == "aweg 23")

    def test_multikey_expansion_to_path(self, spec):
        """
          {blah}/{bloo} -> aweg/wegg
        """
        key = dkey.DKey("{blah}/{bloo}", mark=dkey.DKey.mark.PATH)
        assert(isinstance(key, dkey.MultiDKey))
        assert(isinstance(key, dkey.PathMultiDKey))
        assert(key._exp_type is pl.Path)
        state = {"blah": pl.Path("aweg"), "bloo":"wegg"}
        result = key.expand(spec, state)
        assert(isinstance(result, pl.Path))
        assert(result == pl.Path("aweg/wegg").resolve())

    def test_multikey_path_with_prefix(self, spec):
        """
          --target={blah}/{bloo} -> --target=aweg/wegg
        """
        key = dkey.DKey("--target={blah!p}/{bloo}")
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.PathMultiDKey))
        state = {"blah": pl.Path("aweg"), "bloo":"wegg"}
        result = key.expand(spec, state)
        assert(isinstance(result, str))
        base = doot.locs.normalize(pl.Path("aweg"))
        assert(result == f"--target={base}/wegg")

    def test_multikey_path_with_prefix_enforced_ctor(self, spec):
        """
          --target={blah}/{bloo} -> --target=aweg/wegg
        """
        key = dkey.DKey("--target={blah!p}/{bloo}", ctor=pl.Path)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.PathMultiDKey))
        state = {"blah": pl.Path("aweg"), "bloo":"wegg"}
        result = key.expand(spec, state)
        assert(isinstance(result, pl.Path))
        assert(result == pl.Path("--target={}/wegg".format(doot.locs.normalize(pl.Path("aweg")))))

    def test_multikey_path_direct_fallback_to_indirect(self, spec):
        """
          {main} -> {main_} -> {blah}/{bloo} -> aweg/wegg
        """
        key = dkey.DKey("main", mark=dkey.DKey.mark.PATH)
        state = {"main_":"redir", "redir": "{blah}/{bloo}", "blah": pl.Path("aweg"), "bloo":"wegg"}
        assert(isinstance(key, dkey.SingleDKey))
        assert(isinstance(key, dkey.PathSingleDKey))
        assert(key._exp_type is pl.Path)
        result = key.expand(spec, state)
        assert(isinstance(result, pl.Path))
        assert(result == pl.Path("aweg/wegg").resolve())

    def test_multikey_recursive_expansion(self, spec):
        """
          blah/bloo -> {other}/wegg -> aweg/wegg
        """
        key = dkey.DKey("{blah}/{bloo}", mark=dkey.DKey.mark.PATH)
        assert(isinstance(key, dkey.MultiDKey))
        assert(isinstance(key, dkey.PathMultiDKey))
        assert(key._exp_type is pl.Path)
        state = {"blah": "{other}", "bloo":"wegg", "other": "aweg"}
        result = key.expand(spec, state)
        assert(isinstance(result, pl.Path))
        assert(result == pl.Path("aweg/wegg").resolve())

class TestDKeyRedirection:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "a", "a": 2}))

    def test_sanity(self):
        key = dkey.DKey("x")
        assert(isinstance(key, dkey.DKey))

    def test_redirection(self, spec):
        """
          test_ -> blah
        """
        state = {"test_": "blah", "blah": 23}
        key   = dkey.DKey("test_", mark=dkey.DKey.mark.REDIRECT)
        assert(isinstance(key, dkey.RedirectionDKey))
        result = key.redirect(spec, state)
        assert(result is not None)
        assert(isinstance(result, list))
        assert(result[0] == "blah")

    def test_redirection_remark(self, spec):
        """
          test_ -> blah
        """
        state = {"test_": "blah", "blah": 23}
        key   = dkey.DKey("test_", mark=dkey.DKey.mark.REDIRECT, re_mark=dkey.DKey.mark.PATH)
        assert(isinstance(key, dkey.RedirectionDKey))
        result = key.expand(spec, state)
        assert(result is not None)
        assert(result._mark == dkey.DKey.mark.PATH)

    def test_redirect_prefers_indirect_key_over_direct(self):
        """
          test_ -> blah
        """
        state = {"test_": "blah", "blah": 23}
        key   = dkey.DKey("test_", mark=dkey.DKey.mark.REDIRECT)
        assert(isinstance(key, dkey.RedirectionDKey))
        result = key.expand({"test": "aweg"}, state)
        assert(result is not None)
        assert(isinstance(result, dkey.DKey))
        assert(result == "blah")

    def test_expansion_is_redirection(self, spec):
        """
          test_ -> blah
        """
        state = {"test_": "blah", "blah": 23}
        key   = dkey.DKey("test_", mark=dkey.DKey.mark.REDIRECT)
        assert(isinstance(key, dkey.RedirectionDKey))
        result = key.expand(spec, state)
        assert(result is not None)
        assert(isinstance(result, dkey.DKey))
        assert(result == "blah")

    def test_redirection_null(self, spec):
        """
          test_ -> test_
        """
        state = { "blah": 23}
        key   = dkey.DKey("test_", mark=dkey.DKey.mark.REDIRECT)
        assert(isinstance(key, dkey.RedirectionDKey))
        result = key.redirect(spec, state)
        assert(result is not None)
        assert(isinstance(result, list))
        assert(not isinstance(result[0], dkey.RedirectionDKey))
        assert(result[0] == "test")

    def test_redirection_multi(self, spec):
        """
          test_ -> [a, b, c]
        """
        state = { "test_": ["a", "b", "c"], "blah": 23, "a":10, "b":15, "c":25}
        key   = dkey.DKey("test_", mark=dkey.DKey.mark.REDIRECT)
        assert(isinstance(key, dkey.RedirectionDKey))
        result = key.redirect(spec, state, multi=True)
        assert(result is not None)
        assert(isinstance(result, list))
        assert(len(result) == 3)
        assert(result[0] == "a")
        assert(result[1] == "b")
        assert(result[2] == "c")

    def test_redirection_path(self, spec):
        """
          test -> test_ -> simple
        """
        key   = dkey.DKey("test", mark=dkey.DKey.mark.PATH)
        state = { "test_": "simple", "simple": "blah"}
        assert(isinstance(key, dkey.DKey))
        redir = key.redirect(state)
        assert(redir[0] == "simple")

    def test_redirection_expand_multi_in_ctor(self, spec):
        """
          test_ -> [a, b, c]
        """
        state = { "test_": ["a", "b", "c"], "blah": 23, "a":10, "b":15, "c":25}
        key   = dkey.DKey("test_", mark=dkey.DKey.mark.REDIRECT, multi=True)
        assert(isinstance(key, dkey.RedirectionDKey))
        result = key.expand(spec, state)
        assert(result is not None)
        assert(isinstance(result, list))
        assert(len(result) == 3)
        assert(result[0] == "a")
        assert(result[1] == "b")
        assert(result[2] == "c")

class TestDKeyFormatting:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "a", "a": 2}))

    def test_sanity(self):
        key = dkey.DKey("x")
        fmt = DKeyFormatter()
        result = fmt.format(key)
        assert(result == "x")

    def test_format_with_type_conv(self):
        key           = dkey.DKey("{x}")
        fmt           = DKeyFormatter()
        result        = fmt.format("{x!p}", key)
        assert(result == "x")
