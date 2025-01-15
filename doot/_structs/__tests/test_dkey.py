#!/usr/bin/env python4
"""

"""
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast, Self, Final)
import warnings

import pytest

logging = logmod.root

from jgdv.structs.strang import CodeReference
from jgdv.structs.dkey import DKeyFormatter
from jgdv.structs.strang.locations import JGDVLocations as DootLocations
from jgdv.structs.dkey import implementations as imps

import doot
doot._test_setup()
from doot.utils.testing_fixtures import wrap_locs
from doot._structs.action_spec import ActionSpec
from doot._structs import dkey
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

TEST_LOCS               : Final[DootLocations]       = DootLocations(pl.Path.cwd()).update({"blah": "file::a/b/c.py"})

class TestDKeyTypeParams:

    def test_path_mark(self):
        assert(dkey.PathSingleDKey._mark is dkey.DKey.mark.PATH)

class TestDKeyBasicConstruction:

    def test_implicit_single_path_key(self):
        """ Implicit keys can be marked with conversion params to guide their key type """
        key = dkey.DKey("simple!p", implicit=True)
        assert(key._mark is dkey.DKey.mark.PATH)
        assert(isinstance(key, dkey.PathSingleDKey))

    def test_explicit_path_key(self):
        """ explicit keys can also mark their type """
        key = dkey.DKey("{simple!p}", implicit=False)
        assert(key._mark is dkey.DKey.mark.PATH)
        assert(isinstance(key, dkey.PathSingleDKey))

    def test_re_mark_key(self):
        """ explicit keys can also mark their type """
        key = dkey.DKey("{simple!p}/blah", implicit=False)
        assert(key._mark is dkey.DKey.mark.FREE)
        assert(isinstance(key, dkey.MultiDKey))
        re_marked = dkey.DKey(key, mark=dkey.DKey.mark.PATH)
        assert(isinstance(re_marked, dkey.PathMultiDKey))

    def test_multi_key_with_path_subkey(self):
        """ typed keys within multikeys are allowed,
          it will just be all coerced to a string eventually
        """
        key = dkey.DKey("text. {simple!p}. text.", implicit=False)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.PathMultiDKey))
        assert(key._has_text)
        assert(isinstance(key.keys()[0], dkey.PathSingleDKey))

    def test_multi_key_of_path_subkey(self):
        """ typed keys within multikeys are allowed,
          it will just be all coerced to a string eventually
        """
        key = dkey.DKey("{test!p}", mark=dkey.DKey.mark.MULTI, fallback="{test!p}")
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.PathMultiDKey))
        assert(not key._has_text)
        assert(isinstance(key.keys()[0], dkey.PathSingleDKey))

    def test_multi_keys_with_multiple_subkeys(self):
        """ typed keys within multikeys are allowed,
          it will just be all coerced to a string eventually
        """
        key = dkey.DKey("text. {simple!p}. {text}.", implicit=False)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.PathMultiDKey))
        assert(key._has_text)
        assert(isinstance(key.keys()[0], dkey.PathSingleDKey))
        assert(len(key.keys()) == 2)

    def test_path_keys_from_mark(self):
        """ path keys can be made from an explicit mark """
        key = dkey.DKey("{simple}", implicit=False, mark=dkey.DKey.mark.PATH)
        assert(isinstance(key, dkey.PathSingleDKey))
        assert(not isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.PathMultiDKey))

class TestDKeyWithParameters:
    """ Tests for checking construction with various parameter are preserved """

    def test_conv_params_path_implicit(self):
        obj = dkey.DKey("aval!p", implicit=True)
        assert(isinstance(obj, dkey.PathSingleDKey))

    def test_conv_params_multi_path(self):
        obj = dkey.DKey("{aval!p}/{blah}", mark=dkey.DKey.mark.PATH)
        assert(isinstance(obj, dkey.MultiDKey))
        subkeys = obj.keys()
        assert(len(subkeys) == 2)

    def test_conv_parms_taskname(self):
        obj = dkey.DKey("aval!t", implicit=True)
        assert(isinstance(obj, dkey.TaskNameDKey))

    def test_conflicting_marks_error(self):
        with pytest.raises(ValueError):
            dkey.DKey("{aval!p}", implicit=False, mark=dkey.DKey.mark.CODE)

class TestDKeyExpansion:

    def test_expansion_to_str_for_expansion_with_path(self, wrap_locs):
        wrap_locs.update({"raise": "file::>a/b/blah.py"})
        assert("raise" in wrap_locs)
        state = {"middle": "Before. {raise!p}. After."}
        target        = "Before. {}. After.".format(wrap_locs['{raise}'])
        key           = dkey.DKey("middle", implicit=True)
        result        = key.expand(state)
        assert(key    == "middle")
        assert(result == target)

    def test_expansion_to_str_for_expansion_with_path_expansion(self, wrap_locs):
        wrap_locs.update({"raise": "dir::>{major}/blah", "major": "dir::>head"})
        state = {"middle": "Before. {subpath!p}. After.", "subpath":"{raise!p}/{aweo}", "aweo":"aweg"}
        target        = "Before. {}. After.".format(doot.locs["head/blah/aweg"])
        key           = dkey.DKey("middle", implicit=True)
        result        = key.expand(state)
        assert(key    == "middle")
        assert(result == target)

    def test_expansion_to_taskname(self):
        """
        test -> group::name
        """
        state = {"test": "group::name"}
        key = dkey.DKey("test", mark=dkey.DKey.mark.TASK, implicit=True)
        assert(isinstance(key, dkey.TaskNameDKey))
        result = key.expand(state)
        assert(isinstance(result, TaskName))

class TestDKeyMultikeyExpansion:

    def test_expansion_with_key_conflict(self):
        mk          = dkey.DKey("--blah={test!p}/{test}", mark=dkey.DKey.mark.MULTI)
        transformed = dkey.DKey("--blah={test!p}/{test2}", mark=dkey.DKey.mark.MULTI)
        assert(isinstance(mk, dkey.MultiDKey))
        assert(not isinstance(mk, dkey.PathMultiDKey))
        target      = "--blah=%s" % doot.locs["aweg/aweg"]
        assert(mk._anon == "--blah={}/{}")
        result = mk.expand({"test": "aweg"})
        assert(result == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_path_subkey(self, name):
        """ this is a {name!p} blah. -> this is a ../test blah."""
        target   = "this is a %s blah." % doot.locs["test"]
        full_str = "this is a {%s!p} blah." % name
        key      = dkey.DKey(full_str, implicit=False, mark=dkey.DKey.mark.STR)
        state    = {name : "test"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.PathMultiDKey))
        assert(exp == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_multi_use_path_subkey(self, name):
        """ this is a {name!p} blah {name}. -> this is a ../test blah test."""
        target   = "this is a %s blah test." % doot.locs["test"]
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
        target   = "this is a %s blah something." % doot.locs["test"]
        full_str = "this is a {%s!p} blah {other}." % name
        key      = dkey.DKey(full_str, implicit=False, mark=dkey.DKey.mark.STR)
        state    = {name : "test", "other": "something"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.PathMultiDKey))
        assert(exp == target)

class TestDKeyPathKeys:

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
        assert(exp == doot.locs["y"])

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_explicit(self, name):
        """ {name!p} -> Path(y) """
        path_marked = "{%s!p}" % name
        key   = dkey.DKey(path_marked, implicit=False)
        state = {name :"y"}
        exp   = key.expand(state)
        assert(isinstance(key, dkey.PathSingleDKey))
        assert(isinstance(exp, pl.Path))
        assert(exp == doot.locs["y"])

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_recursive(self, name):
        """ name -> {x} -> Path(y) """
        state = {name :"{x}", "x": "y"}
        path_marked = "{%s!p}" % name
        key   = dkey.DKey(path_marked, implicit=False)
        exp   = key.expand(state)
        assert(isinstance(key, dkey.PathSingleDKey))
        assert(isinstance(exp, pl.Path))
        assert(exp == doot.locs["y"])

    @pytest.mark.parametrize("name", ["a_", "b_"])
    def test_path_marked_redirect(self, name):
        """ {name_!p} -> {x} -> Path(y) """
        path_marked = "{%s}" % name
        key   = dkey.DKey(path_marked, implicit=False)
        state = {name :"x!p", "x": "y"}
        exp   = key.expand(state)
        final = exp.expand(state)
        assert(isinstance(key, imps.RedirectionDKey))
        assert(isinstance(exp, dkey.PathSingleDKey))
        assert(isinstance(final, pl.Path))
        assert(final == doot.locs["y"])

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_multikey(self, name):
        """ {name!p}/{name} -> {x}/{x} -> Path(y/y) """
        state       = {name :"{x}", "x": "y"}
        path_marked = "{%s!p}/x" % name
        target      = str(doot.locs["y/x"])
        key         = dkey.DKey(path_marked, implicit=False)
        exp         = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(exp == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_multikey_with_subpath(self, name, wrap_locs):
        """ {name!p}/{name} -> {x}/{x} -> Path(y/y) """
        wrap_locs.update({"changelog": "file::>sub/changelog.md"})
        state       = {name :"{changelog}"}
        target      = "--test=%s/x {missing}" % wrap_locs.changelog
        path_marked = "--test={%s!p}/x {missing}" % name
        key         = dkey.DKey(path_marked, mark=dkey.DKey.mark.MULTI, implicit=False)
        exp         = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.PathMultiDKey))
        assert(exp == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_fallback_lookup(self, name):
        """
          name -> missing -> fallback
        """
        target = doot.locs["blah"]
        key    = dkey.DKey(name, mark=dkey.DKey.mark.PATH, fallback="blah", implicit=True)
        state  = {}
        exp    = key.expand(state)
        assert(isinstance(key, dkey.PathSingleDKey))
        assert(exp == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_self_fallback(self, name):
        """
          name -> missing -> fallback
        """
        target = doot.locs[name]
        key    = dkey.DKey(name, mark=dkey.DKey.mark.PATH, fallback=Self, implicit=True)
        state  = {}
        exp    = key.expand(state)
        assert(isinstance(key, dkey.PathSingleDKey))
        assert(exp == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_with_none_fallback(self, name):
        """
          name -> missing -> fallback
        """
        target = doot.locs["blah"]
        key    = dkey.DKey(name, mark=dkey.DKey.mark.PATH, fallback=None, implicit=True)
        state  = {}
        exp    = key.expand(state)
        assert(isinstance(key, dkey.PathSingleDKey))
        assert(exp == None)

    def test_cwd_build(self):
        obj = dkey.DKey("__cwd", implicit=True, mark=dkey.DKey.mark.PATH, default=".")
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.PathSingleDKey))
        assert(obj.expand() == pl.Path.cwd())

    def test_cwd_build_with_param(self):
        obj = dkey.DKey("__cwd!p", implicit=True)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.PathSingleDKey))
        assert(obj.expand() == pl.Path.cwd())

    def test_explicit_cwd_with_param(self):
        obj = dkey.DKey("{__cwd!p}", implicit=False, mark=dkey.DKey.mark.MULTI)
        assert(isinstance(obj, dkey.DKey))
        # assert(isinstance(obj, dkey.PathSingleDKey))
        assert(obj.expand() == pl.Path.cwd())

    def test_cwd_without_fallback(self):
        obj = dkey.DKey("__cwd", mark=dkey.DKey.mark.PATH)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.PathSingleDKey))
        assert(obj.expand() == pl.Path.cwd())

    def test_cwd_in_different_location(self):
        with doot.locs(pl.Path("~")) as locs:
            obj = dkey.DKey("__cwd", mark=dkey.DKey.mark.PATH)
            assert(isinstance(obj, dkey.DKey))
            assert(isinstance(obj, dkey.PathSingleDKey))
            assert(obj.expand() == pl.Path("~").expanduser())

    def test_multi_layer_path_key(self, wrap_locs):
        wrap_locs.update({"data_drive": "dir::>/media/john/data", "pdf_source": "dir::>{data_drive}/library/pdfs"})
        state = {}
        obj = dkey.DKey("pdf_source!p", implicit=True)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.PathSingleDKey))
        assert(obj.expand() == pl.Path("/media/john/data/library/pdfs"))

    def test_retrieve_relative_path(self, wrap_locs):
        wrap_locs.update({"data_drive": "/media/john/data", "pdf_source": "{data_drive}/library/pdfs"})
        state = {"relpath": pl.Path("a/b/c"), "head_": "relpath"}
        obj = dkey.DKey("relpath", implicit=True, mark=dkey.DKey.mark.FREE)
        redir = dkey.DKey("head", implicit=True)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.SingleDKey))
        assert(redir.expand(state) == str(pl.Path("a/b/c")))
