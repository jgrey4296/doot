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

import doot
import doot.errors
from doot.utils.testing_fixtures import wrap_tmp
from doot.structs import DootTaskSpec, DootCodeReference
from doot._abstract import TaskBase_i

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

walker_ref = DootCodeReference.from_str("doot.task.base_job:DootJob").add_mixins("doot.mixins.job.shadower:WalkShadowerMixin")
Walker     = walker_ref.try_import()

class TestTreeShadower:

    @pytest.fixture
    def subtree(self, wrap_tmp):
        (wrap_tmp / "subdir").mkdir()
        (wrap_tmp / "subdir/first").mkdir()
        (wrap_tmp / "subdir/second").mkdir()

        (wrap_tmp / "subdir/first/test.bib").touch()
        (wrap_tmp / "subdir/second/blah.bib").touch()
        yield wrap_tmp

    def test_temp_dir_check(self, subtree):
        """ check building a temp directory works """
        contents = list(subtree.iterdir())

        contents = [x.stem for x in (subtree / "subdir").iterdir()]
        assert("first" in contents)
        assert("second" in contents)

    def test_initial(self):
        obj = Walker(DootTaskSpec.from_dict({"name" : "basic"}))
        assert(isinstance(obj, TaskBase_i))


    def test_simple(self, subtree):
        obj = Walker(DootTaskSpec.from_dict(
            {"name"  : "basic",
             "roots" : [ subtree / "subdir" ],
             "exts"  : [".bib"],
             "recursive" : True,
             "shadow_root" : subtree / "shadowed",
             }))
        assert(isinstance(obj, TaskBase_i))
        tasks = list(obj.build())
        assert(bool(tasks))
        for task in tasks:
            if "$head$" in task.name:
                continue
            assert("shadow_path" in task.extra)
            assert(task.extra.shadow_path == subtree / "shadowed" / task.extra.lpath.parent)


    def test_different_shadow(self, subtree):
        obj = Walker(DootTaskSpec.from_dict(
            {"name"  : "basic",
             "roots" : [ subtree / "subdir" ],
             "exts"  : [".bib"],
             "recursive" : True,
             "shadow_root" : subtree / "different",
             }))
        assert(isinstance(obj, TaskBase_i))
        tasks = list(obj.build())
        assert(bool(tasks))
        for task in tasks:
            if "$head$" in task.name:
                continue
            assert("shadow_path" in task.extra)
            assert(task.extra.shadow_path == subtree / "different" / task.extra.lpath.parent)


    def test_error_if_shadowed_is_same_as_root(self, subtree):
        obj = Walker(DootTaskSpec.from_dict(
            {"name"  : "basic",
             "roots" : [ subtree / "subdir" ],
             "exts"  : [".bib"],
             "recursive" : True,
             "shadow_root" : subtree / "subdir",
             }))
        assert(isinstance(obj, TaskBase_i))
        with pytest.raises(doot.errors.DootLocationError):
            list(obj.build())
