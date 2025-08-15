#!/usr/bin/env python3
"""

"""
# Imports:
# ruff: noqa: B011, PLR2004, ANN001, F811, UP031, ANN202
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
import pathlib as pl
import warnings
from typing import (Any, Callable, ClassVar, Final, Generic, Iterable,
                    Iterator, Mapping, Match, MutableMapping, Self, Sequence,
                    Tuple, TypeAlias, TypeVar, cast)

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
from jgdv.structs.dkey import DKey, DKeyed, ImportDKey
from jgdv.structs.dkey._interface import Key_p, MultiKey_p
from jgdv.structs.locator import JGDVLocator as DootLocator
from jgdv.structs.strang import CodeReference, StrangError

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.util import dkey
from doot.util.testing_fixtures import wrap_locs
from doot.workflow.structs.action_spec import ActionSpec
from doot.workflow.structs.task_name import TaskName

# ##-- end 1st party imports

from .. import dkey as dootkeys
# Vars:
logging                                = logmod.root

TEST_LOCS        : Final[DootLocator]  = DootLocator(pl.Path.cwd()).update({"blah": "file::a/b/c.py"})
IMP_KEY_BASES    : Final[list[str]]    = ["bob", "bill", "blah", "other", "23boo", "aweg2531", "awe_weg", "aweg-weji-joi"]
EXP_KEY_BASES    : Final[list[str]]    = [f"{{{x}}}" for x in IMP_KEY_BASES]
EXP_P_KEY_BASES  : Final[list[str]]    = ["{bob:wd}", "{bill:w}", "{blah:wi}", "{other:i}"]
PATH_KEYS        : Final[list[str]]    = ["{bob}/{bill}", "{blah}/{bloo}", "{blah}/{bloo}"]
MUTI_KEYS        : Final[list[str]]    = ["{bob}_{bill}", "{blah} <> {bloo}", "! {blah}! {bloo}!"]
IMP_IND_KEYS     : Final[list[str]]    = ["bob_", "bill_", "blah_", "other_"]
EXP_IND_KEYS     : Final[list[str]]    = [f"{{{x}}}" for x in IMP_IND_KEYS]

VALID_KEYS                             = IMP_KEY_BASES + EXP_KEY_BASES + EXP_P_KEY_BASES + IMP_IND_KEYS + EXP_IND_KEYS
VALID_MULTI_KEYS                       = PATH_KEYS + MUTI_KEYS

# Body:

class TestTaskNameDKey:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_retrieval(self):
        tn_key = DKey[TaskName]
        assert(tn_key is dootkeys.TaskNameDKey)

    def test_basic(self):
        val = DKey[TaskName]
        match DKey[TaskName]("{test}"):
            case dkey.TaskNameDKey() as x:
                assert(DKey.MarkOf(x) == DKey.MarkOf(DKey[TaskName]))
            case x:
                assert(False), type(x)

    @pytest.mark.skip
    def test_todo(self):
        pass

class TestPathMultiKey:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_retrieval(self):
        pathkey = DKey[pl.Path]
        assert(pathkey is dootkeys.DootPathDKey)
        assert(isinstance(pathkey, MultiKey_p))
        assert(isinstance(pathkey, Key_p))

    def test_basic(self):
        match DKey[pl.Path]("{test}"):
            case dkey.DootPathDKey() as x:
                assert(DKey.MarkOf(x) == pl.Path)
                assert(True)
            case x:
                 assert(False), type(x)

    def test_expansion_implicit_hit_loc(self):
        """
        {test} -> blah -> ./blah
        """
        target = pl.Path.cwd() / "blah"
        locs = DootLocator(pl.Path.cwd())
        locs.update({"test": "blah"})
        assert("test" in locs)
        assert(locs['{test!p}'] == target)
        assert(locs.normalize(locs.test) == target)
        key = DKey[pl.Path]("{test}")
        match key.expand(locs):
            case pl.Path() as x:
                assert(x == target)
            case x:
                assert(False), x

    def test_expansion_explicit_loc(self):
        target = pl.Path.cwd() / "test"
        key = DKey[pl.Path]("test")
        assert(isinstance(key, dootkeys.DootPathDKey))
        match key.expand():
            case pl.Path() as x:
                assert(x == target)
            case x:
                assert(False), (type(x), x)

    def test_expansion_loc_miss(self):
        assert(doot.locs is not None)
        key = DKey[pl.Path]("{test}")
        match key.expand(None, {}):
            case None:
                assert(True)
            case x:
                assert(False), x

    def test_expansion_cwd(self):
        assert(doot.locs is not None)
        key = DKey[pl.Path](".")
        match key.expand(None, {}):
            case pl.Path() as x:
                assert(x == pl.Path.cwd())
            case x:
                assert(False), x

    @pytest.mark.skip
    def test_todo(self):
        pass

class TestDKeyBasicConstruction:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_implicit_single_path_key(self):
        """ Implicit keys can be marked with conversion params to guide their key type """
        assert("p" in dkey.DKey._processor.convert_mapping)
        key = dkey.DKey("simple!p", implicit=True)
        assert(DKey.MarkOf(key) is pl.Path)
        assert(isinstance(key, dkey.DootPathDKey))

    def test_explicit_path_key(self):
        """ explicit keys can also mark their type """
        key = dkey.DKey("{simple!p}", implicit=False)
        assert(dkey.DKey.MarkOf(key) is pl.Path)
        assert(isinstance(key, dkey.DootPathDKey))

    def test_multi_key_with_path_subkey(self):
        """ typed keys within multikeys are allowed,
          it will just be all coerced to a string eventually
        """
        key = dkey.DKey("text. {simple!p}. text.")
        key.keys()
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.DootPathDKey))
        assert(isinstance(key.keys()[0], dkey.DootPathDKey))

    def test_multi_key_of_path_subkey(self):
        """ typed keys within multikeys are allowed,
          it will just be all coerced to a string eventually
        """
        key = dkey.DKey("-- {test!p}", fallback="{test!p}")
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.DootPathDKey))
        assert(isinstance(key.keys()[0], dkey.DootPathDKey))

    def test_multi_keys_with_multiple_subkeys(self):
        """ typed keys within multikeys are allowed,
          it will just be all coerced to a string eventually
        """
        key = dkey.DKey("text. {simple!p}. {text}.", implicit=False)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.DootPathDKey))
        assert(isinstance(key.keys()[0], dkey.DootPathDKey))
        assert(len(key.keys()) == 2)

class TestDKeyWithParameters:
    """ Tests for checking construction with various parameter are preserved """

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_conv_params_path_implicit(self):
        obj = dkey.DKey("aval!p", implicit=True)
        assert(isinstance(obj, dkey.DootPathDKey))

    def test_conv_params_multi_path(self):
        obj = dkey.DKey("{aval!p}/{blah}")
        assert(isinstance(obj, dkey.MultiDKey))
        subkeys = obj.keys()
        assert(len(subkeys) == 2)
        assert(isinstance(subkeys[0], dootkeys.DootPathDKey))
        assert(isinstance(subkeys[1], dkey.SingleDKey))

    def test_conv_parms_taskname(self):
        obj = dkey.DKey("aval!t", implicit=True)
        assert(isinstance(obj, dkey.TaskNameDKey))

class TestDKeyExpansion:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_path_expansion(self, wrap_locs):
        wrap_locs.update({"raise": "file::>a/b/blah.py"})
        assert("raise" in wrap_locs)
        target  = pl.Path.cwd() / "a/b/blah.py"
        key     = dkey.DKey("{raise!p}")
        assert(isinstance(key, dkey.DootPathDKey))
        assert(isinstance(target, pl.Path))
        match key.expand(wrap_locs):
            case pl.Path() as x:
                assert(x == target)
            case x:
                assert(False), x

    def test_direct_wrapped_expansion_normalized(self, wrap_locs):
        wrap_locs.update({"raise": "file::>a/b/blah.py"})
        assert("raise" in wrap_locs)
        state       = {"middle": "Before. {raise!p}. After."}
        target      = "Before. {}. After.".format(wrap_locs['{raise}'])
        key         = dkey.DKey("middle", implicit=True)
        assert(key  == "middle")
        match key.expand(state, wrap_locs, relative=False):
            case str() as result:
                assert(result == target)
            case x:
                assert(False), x


    @pytest.mark.xfail
    def test_direct_wrapped_expansion_non_normalized(self, wrap_locs):
        wrap_locs.update({"raise": "file::>a/b/blah.py"})
        assert("raise" in wrap_locs)
        state       = {"middle": "Before. {raise!p}. After."}
        target      = "Before. a/b/blah.py. After."
        key         = dkey.DKey("middle", implicit=True)
        assert(key  == "middle")
        match key.expand(state, wrap_locs, relative=False):
            case str() as result:
                assert(result == target)
            case x:
                assert(False), x

    def test_indirect_wrapped_expansion(self, wrap_locs):
        """
        Checks that additional sources are carried to recursions
        """
        wrap_locs.update({"raise": "dir::>{major}/blah", "major": "dir::>head"})
        state       = {"middle": "Before. {subpath!p}. After.", "subpath":"{raise}/{aweo}", "aweo":"aweg"}
        target      = "Before. {}. After.".format(doot.locs["head/blah/aweg"])
        key         = dkey.DKey("middle", implicit=True)
        assert(key  == "middle")
        match key.expand(state, wrap_locs):
            case DKey():
                assert(False)
            case str() as result:
                assert(result == target)
            case x:
                assert(False), x

    def test_expansion_to_taskname(self):
        """
        test -> group::name
        """
        state = {"test": "group::name"}
        key = dkey.DKey[TaskName]("test", implicit=True)
        target = TaskName("group::name")
        assert(isinstance(key, dkey.TaskNameDKey))
        match key.expand(state):
            case TaskName() as result:
                assert(isinstance(result, TaskName))
            case x:
                 assert(False), x

    def test_expansion_to_taskname_short(self):
        """
        test -> group::name
        """
        state = {"test": "group::name"}
        key = dkey.DKey("{test!t}")
        target = TaskName("group::name")
        assert(isinstance(key, dkey.TaskNameDKey))
        match key.expand(state):
            case TaskName() as result:
                assert(isinstance(result, TaskName))
            case x:
                 assert(False), x

class TestDKeyMultikeyExpansion:

    def test_expansion_with_key_conflict(self):
        mk          = dkey.DKey[list]("--blah={test!p}/{test}")
        transformed = dkey.DKey[list]("--blah={test!p}/{test2}")
        assert(isinstance(mk, dkey.MultiDKey))
        assert(not isinstance(mk, dkey.DootPathDKey))
        target      = "--blah=%s" % doot.locs["aweg/aweg"]
        assert(mk.anon == "--blah={}/{}")
        result = mk.expand({"test": "aweg"})
        assert(result == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_path_subkey(self, name):
        """ this is a {name!p} blah. -> this is a ../test blah."""
        target   = "this is a %s blah." % doot.locs["test"]
        full_str = "this is a {%s!p} blah." % name
        key      = dkey.DKey[list](full_str, implicit=False)
        state    = {name : "test"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.DootPathDKey))
        assert(exp == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_multi_use_path_subkey(self, name):
        """ this is a {name!p} blah {name}. -> this is a ../test blah test."""
        target   = "this is a %s blah test." % doot.locs["test"]
        full_str = "this is a {%s!p} blah {%s}." % (name, name)
        key      = dkey.DKey[list](full_str, implicit=False)
        state    = {name : "test"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.DootPathDKey))
        assert(exp == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_multi_keys(self, name):
        """ this is a {name!p} blah {other}. -> this is a ../test blah something."""
        target   = "this is a %s blah something." % doot.locs["test"]
        full_str = "this is a {%s!p} blah {other}." % name
        key      = dkey.DKey[list](full_str, implicit=False)
        state    = {name : "test", "other": "something"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.DootPathDKey))
        assert(exp == target)

class TestDKeyPathKeys:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_mark_implicit(self, name):
        """ name!p -> Path(y) """
        path_marked = f"{name}!p"
        key   = dkey.DKey(path_marked, implicit=True)
        state = {name :"blah/y"}
        exp   = key.expand(state, relative=True)
        assert(key == name)
        assert(isinstance(key, dkey.DootPathDKey))
        assert(isinstance(exp, pl.Path))
        assert(exp == pl.Path(state[name]))

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_explicit(self, name):
        """ {name!p} -> Path(y) """
        path_marked = "{%s!p}" % name
        key   = dkey.DKey(path_marked, implicit=False)
        state = {name :"y"}
        exp   = key.expand(state, relative=True)
        assert(isinstance(key, dkey.DootPathDKey))
        assert(isinstance(exp, pl.Path))
        assert(exp == pl.Path(state[name]))

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_recursive(self, name):
        """ name -> {x} -> Path(y) """
        state = {name :"{x}", "x": "y"}
        path_marked = "{%s!p}" % name
        key   = dkey.DKey(path_marked, implicit=False)
        exp   = key.expand(state)
        assert(isinstance(key, dkey.DootPathDKey))
        assert(isinstance(exp, pl.Path))
        assert(exp == doot.locs["y"])

    @pytest.mark.parametrize("name", ["a_", "b_"])
    def test_path_marked_redirect(self, name):
        """ {name_} -> {x!p} -> Path(y) """
        path_marked = "{%s}" % name
        key   = dkey.DKey(path_marked)
        state = {name :"x!p", "x": "y"}
        match key.expand(state, limit=1):
            case pl.Path() as val:
                assert(str(val) == "x")
            case x:
                 assert(False), x
        logging.debug("----")
        match key.expand(state):
            case pl.Path() as x:
                assert(x == doot.locs["y"])
            case x:
                 assert(False), x

    @pytest.mark.parametrize("name", ["a_", "b_"])
    def test_redirect_with_conv_param(self, name):
        """ {name_} -> {x!p} -> Path(y) """
        path_marked  = "{%s!p}" % name
        key          = dkey.DKey(path_marked)
        state        = {name  :"x!p", "x": "y"}
        match key.expand(state):
            case pl.Path() as x:
                assert(x == doot.locs["y"])
            case x:
                 assert(False), x

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
        state        = {name :"{changelog}"}
        target_path  = wrap_locs['{changelog}']
        target_str   = "--test=%s/x" % target_path
        key_str      = "--test={%s!p}/x" % name
        key          = dkey.DKey(key_str)
        match key.expand(state, wrap_locs):
            case str() as res:
                assert(res == target_str)
            case x:
                assert(False), x

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_fallback_lookup(self, name):
        """
          name -> missing -> fallback
        """
        target = pl.Path("blah")
        key    = dkey.DKey[pl.Path](name, fallback=pl.Path("blah"), implicit=True)
        state  = {}
        match key.expand(state):
            case pl.Path() as result:
                assert(result == target)
            case x:
                assert(False), x


    @pytest.mark.xfail
    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_self_fallback(self, name):
        """
          name -> missing -> fallback
        """
        key    = dkey.DKey(name, fallback=Self, implicit=True)
        state  = {}
        match key.expand(state):
            case DKey() as result:
                assert(result == key)
            case x:
                assert(False), x

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_with_none_fallback(self, name):
        """
          name -> missing -> fallback
        """
        target = doot.locs["blah"]
        key    = dkey.DKey[pl.Path](name, fallback=None, implicit=True)
        state  = {}
        match key.expand(state):
            case None:
                assert(True)
            case x:
                assert(False), x

    def test_multi_layer_path_key_marked(self, wrap_locs):
        """ Update locs with keys marked as paths.
        ie: {data_drive!p}
        """
        wrap_locs.update({"data_drive": "dir::>/media/john/data",
                          "pdf_source": "dir::>{data_drive!p}/library/pdfs"})
        target = pl.Path("/media/john/data/library/pdfs")
        state  = {}
        obj    = dkey.DKey("pdf_source!p", implicit=True)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.DootPathDKey))
        match obj.expand():
            case pl.Path() as result:
                assert(result == target)
            case x:
                assert(False), x


    @pytest.mark.xfail
    def test_multi_layer_path_key_non_marked(self, wrap_locs):
        """ Update locs with keys *not* marked as paths.
        ie: {data_drive}
        """
        wrap_locs.update({"data_drive": "dir::>/media/john/data",
                          "pdf_source": "dir::>{data_drive}/library/pdfs"})
        target = pl.Path("/media/john/data/library/pdfs")
        state  = {}
        obj    = dkey.DKey("pdf_source!p", implicit=True)
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.DootPathDKey))
        match obj.expand():
            case pl.Path() as result:
                assert(result == target)
            case x:
                assert(False), x

    def test_retrieve_relative_path(self, wrap_locs):
        wrap_locs.update({"data_drive": "/media/john/data",
                          "pdf_source": "{data_drive}/library/pdfs"})
        target = "a/b/c"
        state  = {"relpath": pl.Path("a/b/c")}
        obj    = dkey.DKey("relpath!p", implicit=True)
        assert(isinstance(obj, dkey.DKey))
        match obj.expand(state, relative=True):
            case pl.Path() as result:
                assert(str(result) == target)
            case x:
                 assert(False), x

class TestDKeyedExtension:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_dkey_extended(self):
        assert(dkey.DootKeyed in DKeyed._extensions)

    def test_dkey_getattr_extended(self):
        assert(hasattr(DKeyed, "taskname"))
