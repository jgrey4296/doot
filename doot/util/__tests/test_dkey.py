#!/usr/bin/env python3
"""

"""
# Imports:
# ruff: noqa: E402, ANN201, B011, PLR2004, ANN001, F811, UP031
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
from jgdv.structs.dkey._interface import Key_p
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

    def test_basic(self):
        match DKey("test", force=DKey[TaskName]):
            case dkey.TaskNameDKey() as x:
                assert(DKey.MarkOf(x) == DKey.MarkOf(DKey[TaskName]))
            case x:
                assert(False), x

    @pytest.mark.skip
    def test_todo(self):
        pass

class TestPathSingleKey:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        match DKey("test", force=dkey.DootPathSingleDKey):
            case dkey.DootPathSingleDKey() as x:
                assert(DKey.MarkOf(x) == "doot.path.single")
                assert(True)
            case x:
                 assert(False), x

    def test_expansion_miss(self):
        assert(doot.locs is not None)
        assert("test" not in doot.locs)
        key = DKey("{test}", force=dkey.DootPathSingleDKey)
        match key.expand(None, {}):
            case None:
                assert(True)
            case x:
                 assert(False), x

    def test_expansion_hit(self):
        assert(doot.locs is not None)
        assert("test" not in doot.locs)
        key = DKey("{test}", force=dkey.DootPathSingleDKey)
        match key.expand(None, {"test":"blah"}):
            case pl.Path() as x:
                assert(x == pl.Path.cwd() / "blah")
                assert(True)
            case x:
                 assert(False), x

    def test_expansion_hit_loc(self):
        locs = DootLocator(pl.Path.cwd())
        locs.update({"test": "blah"})
        key = DKey("{test}", force=dkey.DootPathSingleDKey)
        match key.expand(None, locs):
            case pl.Path() as x:
                assert(x == pl.Path.cwd() / "blah")
                assert(True)
            case x:
                 assert(False), x

    def test_expansion_implicit_hit_loc(self):
        locs = DootLocator(pl.Path.cwd())
        locs.update({"test": "blah"})
        key = DKey("test", force=dkey.DootPathSingleDKey, implicit=True)
        match key.expand(None, locs):
            case pl.Path() as x:
                assert(x == pl.Path.cwd() / "blah")
                assert(True)
            case x:
                 assert(False), x

    @pytest.mark.skip
    def test_todo(self):
        pass

@pytest.mark.xfail
class TestPathMultiKey:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        match DKey("test", force=dkey.DootPathMultiDKey):
            case dkey.DootPathMultiDKey() as x:
                assert(DKey.MarkOf(x) == "doot.path.multi")
                assert(True)
            case x:
                 assert(False), x

    def test_expansion_implicit_hit_loc(self):
        """
        {test} -> blah -> ./blah
        """
        target = pl.Path.cwd() / "blah"
        locs = DootLocator(pl.Path.cwd())
        locs.update({"test": "blah"})
        assert("test" in locs)
        assert(locs['{test}'] == target)
        assert(locs.normalize(locs.test) == target)
        key = DKey["doot.path.multi"]("{test}")
        match key.expand(locs):
            case pl.Path() as x:
                assert(x == target)
            case x:
                assert(False), x

    def test_expansion_explicit_loc(self):
        target = pl.Path.cwd() / "test"
        key = DKey("test", force=dkey.DootPathMultiDKey, implicit=False)
        match key.expand():
            case pl.Path() as x:
                assert(x == target)
            case x:
                assert(False), x

    def test_expansion_loc_miss(self):
        assert(doot.locs is not None)
        key = DKey("{test}", mark=DKey.Marks.PATH)
        match key.expand(None, {}):
            case None:
                assert(True)
            case x:
                assert(False), x

    @pytest.mark.xfail
    def test_expansion_cwd(self):
        assert(doot.locs is not None)
        key = DKey(".", mark=DKey.Marks.PATH)
        match key.expand(None, {}):
            case pl.Path() as x:
                assert(x == pl.Path.cwd())
            case x:
                assert(False), x

    @pytest.mark.skip
    def test_todo(self):
        pass

@pytest.mark.xfail
class TestDKeyBasicConstruction:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_implicit_single_path_key(self):
        """ Implicit keys can be marked with conversion params to guide their key type """
        key = dkey.DKey("simple!p", implicit=True)
        assert(DKey.MarkOf(key) is "doot.path.multi")
        assert(isinstance(key, dkey.DootPathSingleDKey))

    def test_explicit_path_key(self):
        """ explicit keys can also mark their type """
        key = dkey.DKey("{simple!p}", implicit=False)
        assert(key.MarkOf() is dkey.DKey.Marks.PATH)
        assert(isinstance(key, dkey.DootPathSingleDKey))

    def test_re_mark_key(self):
        """ explicit keys can also mark their type """
        key = dkey.DKey("{simple!p}/blah", implicit=False)
        assert(key._mark is dkey.DKey.Marks.MULTI)
        assert(isinstance(key, dkey.MultiDKey))
        re_marked = dkey.DKey(key, mark=dkey.DKey.Marks.PATH)
        assert(isinstance(re_marked, dkey.DootPathMultiDKey))

    def test_multi_key_with_path_subkey(self):
        """ typed keys within multikeys are allowed,
          it will just be all coerced to a string eventually
        """
        key = dkey.DKey("text. {simple!p}. text.")
        key.keys()
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.DootPathMultiDKey))
        assert(isinstance(key.keys()[0], dkey.DootPathSingleDKey))

    def test_multi_key_of_path_subkey(self):
        """ typed keys within multikeys are allowed,
          it will just be all coerced to a string eventually
        """
        key = dkey.DKey("-- {test!p}", fallback="{test!p}")
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.DootPathMultiDKey))
        assert(isinstance(key.keys()[0], dkey.DootPathSingleDKey))

    def test_multi_keys_with_multiple_subkeys(self):
        """ typed keys within multikeys are allowed,
          it will just be all coerced to a string eventually
        """
        key = dkey.DKey("text. {simple!p}. {text}.", implicit=False)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.DootPathMultiDKey))
        assert(isinstance(key.keys()[0], dkey.DootPathSingleDKey))
        assert(len(key.keys()) == 2)

    @pytest.mark.xfail
    def test_path_keys_from_mark(self):
        """ path keys can be made from an explicit mark """
        key = dkey.DKey("{simple}", implicit=False, mark=dkey.DKey.Marks.PATH)
        assert(isinstance(key, dkey.DootPathMultiDKey))
        assert(isinstance(key, dkey.MultiDKey))

@pytest.mark.xfail
class TestDKeyWithParameters:
    """ Tests for checking construction with various parameter are preserved """

    def test_conv_params_path_implicit(self):
        obj = dkey.DKey("aval!p", implicit=True)
        assert(isinstance(obj, dkey.DootPathSingleDKey))

    def test_conv_params_multi_path(self):
        obj = dkey.DKey("{aval!p}/{blah}", mark=dkey.DKey.Marks.PATH)
        assert(isinstance(obj, dkey.MultiDKey))
        subkeys = obj.keys()
        assert(len(subkeys) == 2)

    def test_conv_parms_taskname(self):
        obj = dkey.DKey("aval!t", implicit=True)
        assert(isinstance(obj, dkey.TaskNameDKey))

    def test_conflicting_marks_error(self):
        with pytest.raises(StrangError):
            dkey.DKey("{aval!p}", implicit=False, mark=dkey.DKey.Marks.CODE)

@pytest.mark.xfail
class TestDKeyExpansion:

    def test_single_key(self, wrap_locs):
        wrap_locs.update({"raise": "file::>a/b/blah.py"})
        assert("raise" in wrap_locs)
        key = dkey.DKey("{raise!p}")
        target = wrap_locs.norm(pl.Path("a/b/blah.py"))
        assert(isinstance(key, dkey.DootPathSingleDKey))
        match key.expand():
            case pl.Path() as x if x == target:
                assert(True)
            case x:
                assert(False), x

    def test_direct_wrapped_expansion(self, wrap_locs):
        wrap_locs.update({"raise": "file::>a/b/blah.py"})
        assert("raise" in wrap_locs)
        state = {"middle": "Before. {raise!p}. After."}
        target        = "Before. {}. After.".format(wrap_locs['{raise}'])
        key           = dkey.DKey("middle", implicit=True)
        assert(key    == "middle")
        match key.expand(state):
            case dkey.DKey():
                assert(False)
            case str() as result if result == target:
                assert(True)
            case x:
                assert(False), x

    def test_indirect_wrapped_expansion(self, wrap_locs):
        """
        Checks that additional sources are carried to recursions
        """
        wrap_locs.update({"raise": "dir::>{major}/blah", "major": "dir::>head"})
        state = {"middle": "Before. {subpath!p}. After.", "subpath":"{raise!p}/{aweo}", "aweo":"aweg"}
        target        = "Before. {}. After.".format(doot.locs["head/blah/aweg"])
        key           = dkey.DKey("middle", implicit=True)
        assert(key    == "middle")
        match key.expand(state):
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
        key = dkey.DKey("test", mark="taskname", implicit=True)
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
        mk          = dkey.DKey("--blah={test!p}/{test}", mark=dkey.DKey.Marks.MULTI)
        transformed = dkey.DKey("--blah={test!p}/{test2}", mark=dkey.DKey.Marks.MULTI)
        assert(isinstance(mk, dkey.MultiDKey))
        assert(not isinstance(mk, dkey.DootPathMultiDKey))
        target      = "--blah=%s" % doot.locs["aweg/aweg"]
        assert(mk.anon == "--blah={}/{}")
        result = mk.expand({"test": "aweg"})
        assert(result == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_path_subkey(self, name):
        """ this is a {name!p} blah. -> this is a ../test blah."""
        target   = "this is a %s blah." % doot.locs["test"]
        full_str = "this is a {%s!p} blah." % name
        key      = dkey.DKey(full_str, implicit=False, mark=dkey.DKey.Marks.MULTI)
        state    = {name : "test"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.DootPathMultiDKey))
        assert(exp == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_multi_use_path_subkey(self, name):
        """ this is a {name!p} blah {name}. -> this is a ../test blah test."""
        target   = "this is a %s blah test." % doot.locs["test"]
        full_str = "this is a {%s!p} blah {%s}." % (name, name)
        key      = dkey.DKey(full_str, implicit=False, mark=dkey.DKey.Marks.MULTI)
        state    = {name : "test"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.DootPathMultiDKey))
        assert(exp == target)

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_string_expansion_with_multi_keys(self, name):
        """ this is a {name!p} blah {other}. -> this is a ../test blah something."""
        target   = "this is a %s blah something." % doot.locs["test"]
        full_str = "this is a {%s!p} blah {other}." % name
        key      = dkey.DKey(full_str, implicit=False, mark=dkey.DKey.Marks.MULTI)
        state    = {name : "test", "other": "something"}
        exp      = key.expand(state)
        assert(isinstance(key, dkey.MultiDKey))
        assert(not isinstance(key, dkey.DootPathMultiDKey))
        assert(exp == target)

@pytest.mark.xfail
class TestDKeyPathKeys:

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_mark_implicit(self, name):
        """ name!p -> Path(y) """
        path_marked = f"{name}!p"
        key   = dkey.DKey(path_marked, implicit=True)
        state = {name :"y"}
        exp   = key.expand(state)
        assert(key == name)
        assert(isinstance(key, dkey.DootPathSingleDKey))
        assert(isinstance(exp, pl.Path))
        assert(exp == doot.locs["y"])

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_explicit(self, name):
        """ {name!p} -> Path(y) """
        path_marked = "{%s!p}" % name
        key   = dkey.DKey(path_marked, implicit=False)
        state = {name :"y"}
        exp   = key.expand(state)
        assert(isinstance(key, dkey.DootPathSingleDKey))
        assert(isinstance(exp, pl.Path))
        assert(exp == doot.locs["y"])

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_recursive(self, name):
        """ name -> {x} -> Path(y) """
        state = {name :"{x}", "x": "y"}
        path_marked = "{%s!p}" % name
        key   = dkey.DKey(path_marked, implicit=False)
        exp   = key.expand(state)
        assert(isinstance(key, dkey.DootPathSingleDKey))
        assert(isinstance(exp, pl.Path))
        assert(exp == doot.locs["y"])

    @pytest.mark.xfail
    @pytest.mark.parametrize("name", ["a_", "b_"])
    def test_path_marked_redirect(self, name):
        """ {name_} -> {x!p} -> Path(y) """
        path_marked = "{%s}" % name
        key   = dkey.DKey(path_marked, implicit=False, mark=dkey.DKey.Marks.MULTI)
        assert(isinstance(key, dkey.MultiDKey))
        state = {name :"x!p", "x": "y"}
        match key.expand(state, limit=1):
            case str() as x:
                # assert(isinstance(x, dkey.DootPathSingleDKey))
                assert(True)
            case x:
                 assert(False), x
        logging.debug("----")
        match key.expand(state):
            case str() as x:
                assert(x == str(doot.locs["y"]))
            case x:
                 assert(False), x

    @pytest.mark.parametrize("name", ["a_", "b_"])
    def test_redirect_with_conv_param(self, name):
        """ {name_} -> {x!p} -> Path(y) """
        path_marked = "{%s!p}" % name
        key   = dkey.DKey(path_marked, implicit=False)
        state = {name :"x!p", "x": "y"}
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

    @pytest.mark.xfail
    @pytest.mark.parametrize("name", ["a", "b"])
    def test_multikey_with_subpath(self, name, wrap_locs):
        """ {name!p}/{name} -> {x}/{x} -> Path(y/y) """
        wrap_locs.update({"changelog": "file::>sub/changelog.md"})
        state       = {name :"{changelog}"}
        target      = "--test=%s/x" % wrap_locs.normalize(pl.Path(wrap_locs.changelog[1:]))
        path_marked = "--test={%s!p}/x" % name
        key         = dkey.DKey(path_marked, mark=dkey.DKey.Marks.MULTI, implicit=False)
        match key.expand(state):
            case str() as res:
                assert(res == target)
            case x:
                assert(False), x

    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_fallback_lookup(self, name):
        """
          name -> missing -> fallback
        """
        target = "blah"
        key    = dkey.DKey(name, mark=dkey.DKey.Marks.PATH, fallback="blah", implicit=True)
        state  = {}
        match key.expand(state):
            case str() as result:
                assert(result == target)
            case x:
                assert(False), x

    @pytest.mark.xfail
    @pytest.mark.parametrize("name", ["a", "b"])
    def test_path_marked_self_fallback(self, name):
        """
          name -> missing -> fallback
        """
        key    = dkey.DKey(name, mark=dkey.DKey.Marks.PATH, fallback=Self, implicit=True)
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
        key    = dkey.DKey(name, mark=dkey.DKey.Marks.PATH, fallback=None, implicit=True)
        state  = {}
        match key.expand(state):
            case None:
                assert(True)
            case x:
                assert(False), x

    def test_multi_layer_path_key(self, wrap_locs):
        wrap_locs.update({"data_drive": "dir::>/media/john/data", "pdf_source": "dir::>{data_drive}/library/pdfs"})
        state  = {}
        obj    = dkey.DKey("pdf_source!p", implicit=True)
        target = pl.Path("/media/john/data/library/pdfs")
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.DootPathSingleDKey))
        match obj.expand():
            case pl.Path() as result:
                assert(result == target)
            case x:
                assert(False), x

    def test_retrieve_relative_path(self, wrap_locs):
        wrap_locs.update({"data_drive": "/media/john/data", "pdf_source": "{data_drive}/library/pdfs"})
        state  = {"relpath": pl.Path("a/b/c"), "head_": "relpath"}
        obj    = dkey.DKey("relpath", implicit=True, mark=dkey.DKey.Marks.FREE)
        redir  = dkey.DKey("head", implicit=True)
        target = "a/b/c"
        assert(isinstance(obj, dkey.DKey))
        assert(isinstance(obj, dkey.SingleDKey))
        match redir.expand(state):
            case str() as result:
                assert(result == target)
            case x:
                 assert(False), x

class TestDKeyedExtension:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_dkey_extended(self):
        assert(dkey.DootKeyed in DKeyed._extensions)

    def test_dkey_getattr_extended(self):
        assert(hasattr(DKeyed, "taskname"))
