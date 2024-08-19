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
from doot.utils.testing_fixtures import wrap_locs
from doot.control.locations import DootLocations
from doot._structs.action_spec import ActionSpec
from doot._structs import dkey as dkey
from doot.utils.dkey_formatter import DKeyFormatter
from doot._structs.code_ref import CodeReference
from doot._abstract.protocols import Key_p
from doot.structs import TaskName

IMP_KEY_BASES               : Final[list[str]]           = ["bob", "bill", "blah", "other", "23boo", "aweg2531", "awe_weg", "aweg-weji-joi"]
EXP_KEY_BASES               : Final[list[str]]           = [f"{{{x}}}" for x in IMP_KEY_BASES]
EXP_P_KEY_BASES             : Final[list[str]]           = ["{bob:wd}", "{bill:w}", "{blah:wi}", "{other:i}"]
PATH_KEYS                   : Final[list[str]]           = ["{bob}/{bill}", "{blah}/{bloo}", "{blah}/{bloo}"]
MUTI_KEYS                   : Final[list[str]]           = ["{bob}_{bill}", "{blah} <> {bloo}", "! {blah}! {bloo}!"]
IMP_IND_KEYS                : Final[list[str]]           = ["bob_", "bill_", "blah_", "other_"]
EXP_IND_KEYS                : Final[list[str]]           = [f"{{{x}}}" for x in IMP_IND_KEYS]

VALID_KEYS                                           = IMP_KEY_BASES + EXP_KEY_BASES + EXP_P_KEY_BASES + IMP_IND_KEYS + EXP_IND_KEYS
VALID_MULTI_KEYS                                     = PATH_KEYS + MUTI_KEYS

TEST_LOCS               : Final[DootLocations]       = DootLocations(pl.Path.cwd()).update({"blah": "doot"})

class TestDKeyMetaSetup:

    def test_sanity(self):
        key  = dkey.DKey("test", implicit=True)
        assert(isinstance(key, dkey.SingleDKey))
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, str))
        assert(isinstance(key, Key_p))
        assert(f"{key:w}" == "{test}")
        assert(f"{key:i}" == "test_")
        assert(str(key) == "test")

    def test_subclass_registration(self):
        assert(dkey.DKey.get_ctor(dkey.DKeyMark_e.FREE) == dkey.SingleDKey)

        class PretendDKey(dkey.DKeyBase, mark=dkey.DKeyMark_e.FREE):
            pass
        assert(dkey.DKey.get_ctor(dkey.DKeyMark_e.FREE) == PretendDKey)
        # return the original class
        dkey.DKey.register_key(dkey.SingleDKey, dkey.DKeyMark_e.FREE)

    def test_subclass_check(self):
        for x in dkey.DKey._single_registry.values():
            assert(issubclass(x, dkey.DKey))
            assert(issubclass(x, (dkey.SingleDKey, dkey.NonDKey)))

        for x in dkey.DKey._multi_registry.values():
            assert(issubclass(x, dkey.DKey))
            assert(issubclass(x, dkey.MultiDKey))

    def test_subclass_creation_fail(self):
        with pytest.raises(RuntimeError):
            dkey.SingleDKey("test")

    def test_subclass_creation_force(self):
        key = dkey.SingleDKey("test", force=True)
        assert(key is not None)
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, dkey.SingleDKey))

class TestDKeyBasicConstruction:

    def test_initial_implicit(self):
        key  = dkey.DKey("test", implicit=True)
        assert(isinstance(key, dkey.SingleDKey))
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, str))
        assert(f"{key:w}" == "{test}")
        assert(f"{key:i}" == "test_")
        assert(f"{key:wi}" == "{test_}")
        assert(str(key) == "test")

    def test_initial_explicit(self):
        key  = dkey.DKey("{test}")
        assert(isinstance(key, dkey.MultiDKey))
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, str))
        assert(str(key) == "{test}")

    def test_initial_multi_key(self):
        key  = dkey.DKey("{test}/{blah}")
        assert(isinstance(key, dkey.MultiDKey))
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, str))
        assert(key._fparams is None)
        assert(key.keys() == [dkey.DKey("test"), dkey.DKey("blah")])
        assert(str(key) == "{test}/{blah}")

    def test_initial_multi_key_ignores_implicit(self):
        key = dkey.DKey("{test}/{blah}", implicit=True)
        assert(isinstance(key, dkey.MultiDKey))
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, str))
        assert(key._fparams is None)
        assert(key.keys() == [dkey.DKey("test"), dkey.DKey("blah")])
        assert(str(key) == "{test}/{blah}")

    def test_multikey_expansion_with_key_conflict(self):
        mk          = dkey.DKey("--blah={test!p}/{test}", mark=dkey.DKey.mark.MULTI)
        transformed = dkey.DKey("--blah={test!p}/{test2}", mark=dkey.DKey.mark.MULTI)
        target      = "--blah=%s" % pl.Path("aweg/aweg").resolve()
        assert(mk._unnamed == "--blah={}/{}")
        result = mk.expand({"test": "aweg"})
        assert(result == target)

    def test_initial_nonkey(self):
        key  = dkey.DKey("blah bloo blee")
        assert(isinstance(key, dkey.NonDKey))
        assert(isinstance(key, str))
        assert(isinstance(key, dkey.DKey))
        assert(str(key) == "blah bloo blee")

class TestDKeySubclasses:

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_base_key(self, name):
        obj = dkey.DKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))
        assert("{" not in obj)
        assert(hasattr(obj, "_fparams"))

    @pytest.mark.parametrize("name", ["{bob!p}/{bill}"])
    def test_build_path_key_from_str(self, name):
        obj = dkey.DKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.MultiDKey))
        assert(isinstance(obj, dkey.PathMultiDKey))
        assert(isinstance(obj, str))
        assert(obj._exp_type is pl.Path)

    @pytest.mark.parametrize("name", VALID_KEYS)
    @pytest.mark.parametrize("check", [int,str,int|float,list[int],list[str|float], Any, None])
    def test_build_with_typecheck(self, name, check):
        obj = dkey.DKey(name, check=check)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))
        assert(obj._typecheck == check or Any)

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_key_str(self, name):
        """ keys are subclasses of str """
        obj = dkey.DKey(name, implicit=True)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, str))
        assert(str(obj) == name)

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
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
    @pytest.mark.parametrize("name", PATH_KEYS)
    def test_keys_error_on_multi_keys(self, name):
        with pytest.raises(ValueError):
            dkey.SingleDKey(name)

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_build_explicit_(self, name):
        """
          explicit single keys have their braces removed
        """
        explicit = "".join(["{", name, "}"])
        obj = dkey.DKey(explicit)
        assert(isinstance(obj, dkey.DKey))
        assert(str(obj) == explicit)

    @pytest.mark.parametrize("name", PATH_KEYS + MUTI_KEYS)
    def test_multi_build(self, name):
        """
          Keys with multiple expansion points are built as multi keys
        """
        obj = dkey.DKey(name)
        assert(isinstance(obj, dkey.DKey))
        assert(not isinstance(obj, dkey.SingleDKey))
        assert(isinstance(obj, dkey.MultiDKey))

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
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

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_build_non_key(self, name):
        obj = dkey.DKey(name, implicit=False)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.NonDKey))

    @pytest.mark.parametrize("name", IMP_IND_KEYS)
    def test_build_implicit_indirect(self, name):
        obj = dkey.DKey(name, implicit=True)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.SingleDKey))
        assert(isinstance(obj, dkey.RedirectionDKey))
        assert(str(obj) == name)

    def test_integrated_str_keys(self):
        obj = dkey.DKey("--{raise}")
        assert(str(obj) == "--{raise}")

class TestDKeyWithParameters:

    def test_simple_with_fparams(self):
        key  = dkey.DKey("{test:w}")
        assert(isinstance(key, dkey.MultiDKey))
        assert(isinstance(key, dkey.DKey))
        assert(isinstance(key, str))
        assert(bool(key.keys()))
        subkey = key.keys()[0]
        assert(subkey == "test")
        assert(isinstance(subkey, dkey.SingleDKey))
        assert(subkey._fparams == "w")

    def test_init_with_fparams(self):
        key  = dkey.DKey("{test:w}")
        assert(isinstance(key, dkey.MultiDKey))
        assert(bool(key.keys()))
        subkey = key.keys()[0]
        assert(subkey == "test")
        assert(isinstance(subkey, dkey.SingleDKey))
        assert(subkey._fparams == "w")

    def test_conv_params_path_implicit(self):
        obj = dkey.DKey("aval!p", implicit=True)
        assert(isinstance(obj, dkey.SingleDKey))

    def test_conv_params_multi_path(self):
        obj = dkey.DKey("{aval!p}/{blah}")
        assert(isinstance(obj, dkey.PathMultiDKey))
        subkeys = obj.keys()
        assert(len(subkeys) == 2)

    def test_conv_parms_redirect(self):
        obj = dkey.DKey("aval!R", implicit=True)
        assert(isinstance(obj, dkey.RedirectionDKey))

    def test_conv_params_code(self):
        obj = dkey.DKey("aval!c", implicit=True)
        assert(isinstance(obj, dkey.ImportDKey))

    def test_conv_parms_taskname(self):
        obj = dkey.DKey("aval!t", implicit=True)
        assert(isinstance(obj, dkey.TaskNameDKey))

    def test_explicit_mark_overrules_conv_param(self):
        key = dkey.DKey("aval!p", implicit=True, mark=dkey.DKey.mark.CODE)
        assert(isinstance(key, dkey.ImportDKey))

class TestDKeyDunderFormatting:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec(kwargs=TomlGuard({"y": "aweg", "z_": "bloo", "a": 2}))

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_repr(self, name):
        key = dkey.DKey(name, implicit=True)
        assert(repr(key) == f"<SingleDKey: {key}>")

    @pytest.mark.parametrize("name", PATH_KEYS)
    def test_multi_repr(self, name):
        key = dkey.DKey(name)
        assert(repr(key) == f"<MultiDKey: {key}>")

    @pytest.mark.parametrize("name", IMP_KEY_BASES + EXP_KEY_BASES)
    def test_initial_fstr(self, spec, name):
        """ key -> key"""
        key           = dkey.DKey(name)
        result        = f"{key}"
        assert(result == name)

    @pytest.mark.parametrize("name", IMP_IND_KEYS + EXP_KEY_BASES)
    def test_fstr_indirect(self, spec, name):
        """ keys_ -> keys_"""
        key           = dkey.DKey(name)
        result        = f"{key}"
        assert(result == name)

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_fstr_explicit_from_implicit(self, spec, name):
        """ key -> {key} """
        key           = dkey.DKey(name, implicit=True)
        result        = f"{key:w}"
        assert(result == "".join(["{", name, "}"]))

    @pytest.mark.parametrize("name", IMP_IND_KEYS)
    def test_fstr_explicit_indirect(self, spec, name):
        """ keys_ -> {keys_}"""
        key           = dkey.DKey(name, implicit=True)
        result        = f"{key:wi}"
        assert(result == "".join(["{", name, "}"]))

    @pytest.mark.parametrize("name", IMP_KEY_BASES + IMP_IND_KEYS)
    def test_coerce_indirect_to_wrapped_direct(self, spec, name):
        """ key_ -> {key} """
        key           = dkey.DKey(name, implicit=True)
        result        = f"{key:wd}"
        assert(result == "".join(["{", name.removesuffix("_"), "}"]))

    @pytest.mark.parametrize("name", PATH_KEYS)
    def test_fstr_multi_key(self, spec, name):
        """ multi keys are explicit by default """
        key           = dkey.DKey(name)
        result        = f"{key}"
        assert(result == name)
        assert(bool(key.keys()))

    @pytest.mark.parametrize("name", PATH_KEYS)
    def test_fstr_multi_explicit(self, spec, name):
        """ specifying alt form does nothing """
        key           = dkey.DKey(name)
        explicit = f"{key:w}"
        implicit = f"{key:i}"
        assert(explicit == name == implicit)
        assert(bool(key.keys()))

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_fstr_non_key(self, spec, name):
        """ non keys cant be explicit, specifying alt form does nothing """
        key           = dkey.DKey(name, implicit=False)
        assert(isinstance(key, dkey.NonDKey))
        explicit = f"{key:w}"
        implicit = f"{key}"
        assert(explicit == name == implicit)

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_str_format(self, name):
        key = dkey.DKey(name)
        result = "{}".format(key)
        assert(result == name)

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_fstr_format(self, name):
        key = dkey.DKey(name)
        result = f"{key}"
        assert(result == name)

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_fstr_with_width(self, name):
        key = dkey.DKey(name)
        result = f"{key: <5}"
        assert(result == f"{name: <5}")

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_nonkey_format(self, name):
        key           = dkey.DKey(name, implicit=False)
        result        = f"{key}"
        assert(result == name)

    @pytest.mark.parametrize("name", PATH_KEYS)
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

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_key_and_str(self, name):
        """ both __and__ + __rand__ """
        key      = dkey.DKey(name, implicit=True)
        test_str = "this is a {} test".format(f"{key:w}")
        assert(key & test_str)
        assert(test_str & key)

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_key_and_str_fail(self, name):
        """ both __and__ + __rand__ """
        key      = dkey.DKey(name, implicit=True)
        test_str = "this is a {} test".format(f"{key}")
        assert(not (key & test_str))
        assert(not (test_str & key))

    @pytest.mark.parametrize("name", IMP_KEY_BASES)
    def test_key_eq(self, name):
        """   """
        key      = dkey.DKey(name)
        assert( key == name )

class TestDKeyExpansion:

    def test_recursive_expansion_str(self):
        """
          top -> b -> {b}
        """
        key = dkey.DKey("top", implicit=True)
        assert(isinstance(key, dkey.DKey))
        state = {"top_": "b", "b": "{b}"}
        result = key.expand(state)
        assert(result == "{b}")

    def test_expansion_explicit_key(self):
        key = dkey.DKey("--{raise}")
        result = key.expand({"raise":"minor"})
        assert(key == "--{raise}")
        assert(result == "--minor")

    def test_expansion_with_type_spec_in_str(self):
        """ check setting expansion parameters directly from the initial string
          {a!s} -> 2:str
          """
        key   = dkey.DKey("{a!s}")
        state = {"a": 2}
        assert(isinstance(key, dkey.DKey))
        result = key.expand(state)
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

    def test_nested_expansion(self):
        """
          top -> {y} : {a} -> aweg : 2
        """
        key = dkey.DKey("top", implicit=True)
        assert(isinstance(key, dkey.DKey))
        state = {"top": "{y} : {a}", "y": "aweg", "a": 2}
        result = key.expand(state)
        assert(result == "aweg : 2")

    def test_redirection_multi(self):
        """
          test_ -> [a, b, c]
        """
        state = { "test_": ["a", "b", "c"], "blah": 23, "a":10, "b":15, "c":25}
        key   = dkey.DKey("test_", mark=dkey.DKey.mark.REDIRECT)
        assert(isinstance(key, dkey.RedirectionDKey))
        result = key.redirect(state, multi=True)
        assert(result is not None)
        assert(isinstance(result, list))
        assert(len(result) == 3)
        assert(result[0] == "a")
        assert(result[1] == "b")
        assert(result[2] == "c")

    def test_redirection_expand_multi_in_ctor(self):
        """
          test_ -> [a, b, c]
        """
        state = { "test_": ["a", "b", "c"], "blah": 23, "a":10, "b":15, "c":25}
        key   = dkey.DKey("test_", mark=dkey.DKey.mark.REDIRECT, multi=True)
        assert(isinstance(key, dkey.RedirectionDKey))
        result = key.expand(state)
        assert(result is not None)
        assert(isinstance(result, list))
        assert(len(result) == 3)
        assert(result[0] == "a")
        assert(result[1] == "b")
        assert(result[2] == "c")

class TestDKeyExpansionMain:

    def test_initial(self):
        key = dkey.DKey("test")
        assert(isinstance(key, dkey.DKey))

    @pytest.mark.parametrize("name", ["x", "a", "b"])
    def test_basic_construction(self, name):
        key = dkey.DKey(name, implicit=True)
        assert(key == name)

    @pytest.mark.parametrize("name", ["x"])
    def test_basic_expansion(self, name):
        """ name -> y """
        implicit_key   = dkey.DKey(name, implicit=True)
        explicit_key   = dkey.DKey(("{%s}" % name))
        state = {name :"y"}
        assert(implicit_key.expand(state) == "y")
        assert(explicit_key.expand(state) == "y")

    @pytest.mark.parametrize("name", ["x"])
    def test_basic_multikey_expansion(self, name):
        """ name -> y """
        implicit_key   = dkey.DKey(name, mark=dkey.DKey.mark.MULTI, implicit=True)
        explicit_key   = dkey.DKey(("{%s}" % name), mark=dkey.DKey.mark.MULTI)
        state = {name :"y"}
        assert(implicit_key.expand(state) == "y")
        assert(explicit_key.expand(state) == "y")

    def test_multikey_no_keys_expansion(self):
        """ blah test -> blah test """
        implicit_key   = dkey.DKey("blah test", fallback="blah test", mark=dkey.DKey.mark.MULTI, implicit=True)
        explicit_key   = dkey.DKey("blah test", fallback="blah test", mark=dkey.DKey.mark.MULTI)
        state = {"test": "y"}
        assert(implicit_key.expand(state) == "blah test")
        assert(explicit_key.expand(state) == "blah test")

    @pytest.mark.parametrize("name", ["x"])
    def test_basic_non_str_expansion(self, name):
        """ name -> 2 """
        key   = dkey.DKey(name, implicit=True)
        state = {name :2}
        exp = key.expand(state)
        assert(not isinstance(exp, str))
        assert(exp == 2)

    @pytest.mark.parametrize("name", ["x"])
    def test_basic_type_check(self, name):
        """ name -> 2 """
        key   = dkey.DKey(name, implicit=True, check=int)
        state = {name :2}
        exp = key.expand(state)
        assert(not isinstance(exp, str))
        assert(exp == 2)

    @pytest.mark.parametrize("name", ["x"])
    def test_basic_type_check_fail(self, name):
        """ name -> 2 """
        key   = dkey.DKey(name, implicit=True, check=set)
        state = {name :2}
        with pytest.raises(TypeError):
            key.expand(state)

    @pytest.mark.parametrize("name", ["x"])
    def test_expansion_no_state(self, name):
        """ name -> None """
        target = "{%s}" % name
        key        = dkey.DKey(name, implicit=True)
        state      = {}
        exp        = key.expand(state)
        assert(exp == None)

    @pytest.mark.parametrize("name", ["x"])
    def test_expansion_fallback(self, name):
        """ name -> blah"""
        target = "{%s}" % name
        key        = dkey.DKey(name, implicit=True)
        state      = {}
        exp        = key.expand(state, fallback="blah")
        assert(exp == "blah")

    @pytest.mark.parametrize("name", ["x"])
    def test_expansion_nochain(self, name):
        """ name -> y """
        key   = dkey.DKey(name, implicit=True)
        state = {name :"y", "y": "blah"}
        exp = key.expand(state)
        assert(exp == "y")

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_chain_expansion(self, name):
        """ name -> {x} -> y """
        key   = dkey.DKey(name, implicit=True)
        state = {name :"{x}", "x": "y"}
        exp = key.expand(state)
        assert(exp == "y")

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_chain_expand_literal_key(self, name):
        """ name -> DKey(x) -> y """
        key   = dkey.DKey(name, implicit=True)
        state = {name : dkey.DKey("x", implicit=True), "x": "y"}
        exp = key.expand(state)
        assert(exp == "y")

    @pytest.mark.parametrize("name", ["a_", "b_", "blah_bloo_"])
    def test_redirect_expansion(self, name):
        """ name_ -> DKey(x) -> y"""
        key   = dkey.DKey(name, implicit=True)
        state = {name :"x", "x": "y"}
        redir = key.expand(state)
        exp   = redir.expand(state)
        assert(isinstance(redir, dkey.DKey))
        assert(key == name)
        assert(exp == "y")

    @pytest.mark.parametrize("name", ["a", "b", "blah_bloo"])
    def test_redirect_preferred(self, name):
        """
          name -> DKey(x)  -> y
          name_ -> DKey(x) -> y
        """
        name_              = f"{name}_"
        key_direct         = dkey.DKey(name, implicit=True)
        key_indirect       = dkey.DKey(name_, implicit=True)
        state              = {name :"blah", "x": "y", name_: "x"}
        redir              = key_indirect.expand(state)
        indir_exp          = redir.expand(state)
        dir_exp            = key_direct.expand(state)
        assert(isinstance(redir, dkey.DKey))
        assert(key_indirect == name_)
        assert(key_direct == name)
        assert(indir_exp == "y")
        assert(dir_exp == "y")

    @pytest.mark.parametrize("name", ["a", "b", "blah_bloo"])
    def test_redirect_fallbacks_to_actual(self, name):
        """ name_ -> name -> y"""
        name_     = f"{name}_"
        key       = dkey.DKey(name_, implicit=True)
        state     = {name :"y"}
        redir     = key.expand(state)
        exp       = redir.expand(state)
        assert(isinstance(redir, dkey.DKey))
        assert(key == name_)
        assert(exp == "y")

    @pytest.mark.parametrize("name", ["a_", "b_"])
    def test_redirect_full_expansion(self, name):
        """ name_ -> y"""
        key   = dkey.DKey(name, implicit=True)
        state = {name :"x", "x": "y"}
        exp   = key.expand(state, full=True)
        assert(exp == "y")

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_mark_implicit(self, name):
        """ name!p -> Path(y) """
        path_marked = f"{name}!p"
        key   = dkey.DKey(path_marked, implicit=True)
        state = {name :"y"}
        exp   = key.expand(state)
        assert(key == name)
        assert(isinstance(key, dkey.PathSingleDKey))
        assert(isinstance(exp, pl.Path))
        assert(exp == pl.Path("y").resolve())

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_explicit(self, name):
        """ {name!p} -> Path(y) """
        path_marked = "{%s!p}" % name
        key   = dkey.DKey(path_marked, implicit=False)
        state = {name :"y"}
        exp   = key.expand(state)
        assert(isinstance(key, dkey.PathMultiDKey))
        assert(isinstance(exp, pl.Path))
        assert(exp == pl.Path("y").resolve())

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_recursive(self, name):
        """ name -> {x} -> Path(y) """
        path_marked = "{%s!p}" % name
        key   = dkey.DKey(path_marked, implicit=False)
        state = {name :"{x}", "x": "y"}
        exp   = key.expand(state)
        assert(isinstance(key, dkey.PathMultiDKey))
        assert(isinstance(exp, pl.Path))
        assert(exp == pl.Path("y").resolve())

    @pytest.mark.parametrize("name", ["a_", "b_"])
    def test_path_marked_redirect(self, name):
        """ {name_!p} -> {x} -> Path(y) """
        path_marked = "{%s!p}" % name
        key   = dkey.DKey(path_marked, implicit=False)
        state = {name :"x", "x": "y"}
        exp   = key.expand(state)
        assert(isinstance(key, dkey.PathMultiDKey))
        assert(isinstance(exp, pl.Path))
        assert(exp == pl.Path("y").resolve())

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_multikey(self, name):
        """ {name!p}/{name} -> {x}/{x} -> Path(y/y) """
        target = pl.Path("y/x").resolve()
        path_marked = "{%s!p}/x" % name
        key   = dkey.DKey(path_marked, implicit=False)
        state = {name :"{x}", "x": "y"}
        exp   = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(isinstance(key, dkey.PathMultiDKey))
        assert(exp == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_multikey_with_subpath(self, name, wrap_locs):
        """ {name!p}/{name} -> {x}/{x} -> Path(y/y) """
        wrap_locs.update({"changelog": "sub/changelog.md"})
        target      = "--test=%s/x {missing}" % wrap_locs.changelog
        path_marked = "--test={%s!p}/x {missing}" % name
        key         = dkey.DKey(path_marked, mark=dkey.DKey.mark.MULTI, implicit=False)
        state       = {name :"{changelog}"}
        exp         = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.PathMultiDKey))
        assert(exp == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_fallback(self, name):
        """
          name -> missing -> fallback
        """
        target = pl.Path("blah").resolve()
        key   = dkey.DKey(name, mark=dkey.DKey.mark.PATH, fallback="blah", implicit=True)
        state = {}
        exp   = key.expand(state)
        assert(isinstance(key, dkey.PathSingleDKey))
        assert(exp == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_subkey(self, name):
        """ this is a {name} blah. -> this is a test blah."""
        full_str = "this is a {%s} blah." % name
        key      = dkey.DKey(full_str, implicit=False, mark=dkey.DKey.mark.STR)
        state    = {name : "test"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(exp == "this is a test blah.")

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_multi_use_subkey(self, name):
        """ this is a {name} blah {name}. -> this is a test blah test."""
        full_str = "this is a {%s} blah {c}." % name
        key      = dkey.DKey(full_str, implicit=False, mark=dkey.DKey.mark.STR)
        state    = {name : "test", "c": "test"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(exp == "this is a test blah test.")

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_multi_subkeys(self, name):
        """ this is a {name} blah {name}. -> this is a test blah test."""
        full_str = "this is a {%s} blah {bloo}." % name
        key      = dkey.DKey(full_str, implicit=False, mark=dkey.DKey.mark.STR)
        state    = {name : "test", "bloo": "other"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(exp == "this is a test blah other.")

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_path_subkey(self, name):
        """ this is a {name!p} blah. -> this is a ../test blah."""
        target   = "this is a %s blah." % pl.Path("test").resolve()
        full_str = "this is a {%s!p} blah." % name
        key      = dkey.DKey(full_str, implicit=False, mark=dkey.DKey.mark.STR)
        state    = {name : "test"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.PathMultiDKey))
        assert(exp == target)

    @pytest.mark.xfail
    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_multi_use_path_subkey(self, name):
        """ this is a {name!p} blah {name}. -> this is a ../test blah test."""
        target   = "this is a %s blah test." % pl.Path("test").resolve()
        full_str = "this is a {%s!p} blah {%s}." % (name, name)
        key      = dkey.DKey(full_str, implicit=False, mark=dkey.DKey.mark.STR)
        state    = {name : "test"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.PathMultiDKey))
        assert(exp == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_multi_keys(self, name):
        """ this is a {name!p} blah {other}. -> this is a ../test blah something."""
        target   = "this is a %s blah something." % pl.Path("test").resolve()
        full_str = "this is a {%s!p} blah {other}." % name
        key      = dkey.DKey(full_str, implicit=False, mark=dkey.DKey.mark.STR)
        state    = {name : "test", "other": "something"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.PathMultiDKey))
        assert(exp == target)

    def test_cwd_build(self):
        obj = dkey.DKey(".", fallback=".", mark=dkey.DKey.mark.PATH)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.PathSingleDKey))
        assert(obj.expand() == pl.Path.cwd())

    def test_coderef_expansion(self):
        """
          test -> coderef
        """
        state = {"test": "doot._structs.task_spec:TaskSpec"}
        key   = dkey.DKey("test", mark=dkey.DKey.mark.CODE)
        assert(isinstance(key, dkey.DKey))
        result = key.expand(state)
        assert(isinstance(result, CodeReference))
