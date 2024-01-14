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

walker_ref = DootCodeReference.from_str("doot.task.base_job:DootJob").add_mixins("doot.mixins.job.walker:WalkerMixin")
Walker     = walker_ref.try_import()

class TestWalker:


    def test_temp_dir_check(self, wrap_tmp):
        """ check building a temp directory works """
        contents = list(wrap_tmp.iterdir())
        assert(not bool(contents))
        (wrap_tmp / "first").mkdir()
        (wrap_tmp / "second").mkdir()

        contents = [x.stem for x in wrap_tmp.iterdir()]
        assert("first" in contents)
        assert("second" in contents)

    def test_initial(self):
        obj = Walker(DootTaskSpec.from_dict({"name" : "basic"}))
        assert(isinstance(obj, TaskBase_i))

    def test_basic_walk(self, wrap_tmp):
        (wrap_tmp / "first").mkdir()
        (wrap_tmp / "second").mkdir()
        obj = Walker(DootTaskSpec.from_dict({"name" : "basic"}))

        count = 0
        for sub in obj.build():
            logging.debug("Built Subtask: %s", sub.name)
            count += 1
            assert(isinstance(sub, DootTaskSpec))
            assert(str(sub.name) in ["default::basic.first", "default::basic.second", "default::basic.$head$", "default::basic.test_root"])

        assert(count == 4)

    def test_test_file_walk(self, wrap_tmp):
        (wrap_tmp / "first").mkdir()
        (wrap_tmp / "first" / "blah.txt").touch()
        (wrap_tmp / "second").mkdir()
        (wrap_tmp / "second" / "bloo.txt").touch()

        obj = Walker(DootTaskSpec.from_dict({"name" : "basic", "exts" : [".txt"], "recursive": True}))

        count = 0
        for sub in obj.build():
            count += 1
            assert(isinstance(sub, DootTaskSpec))
            assert(str(sub.name) in ["default::basic.blah", "default::basic.bloo", "default::basic.$head$"])

        assert(count == 3)


    def test_only_matching_extensions(self, wrap_tmp):
        (wrap_tmp / "first").mkdir()
        (wrap_tmp / "first" / "blah.txt").touch()
        (wrap_tmp / "first" / "bad.ext").touch()
        (wrap_tmp / "second").mkdir()
        (wrap_tmp / "second" / "bloo.txt").touch()
        (wrap_tmp / "second" / "bibble.blib").touch()

        obj = Walker(DootTaskSpec.from_dict({"name" : "basic", "exts" : [".txt"], "recursive": True}))

        count = 0
        for sub in obj.build():
            count += 1
            assert(isinstance(sub, DootTaskSpec))
            assert(str(sub.name) not in ["default::basic.bad", "default::basic.bibble"])

        assert(count == 3)


    def test_test_no_rec(self, wrap_tmp):
        (wrap_tmp / "first").mkdir()
        (wrap_tmp / "first" / "blah.txt").touch()
        (wrap_tmp / "second").mkdir()
        (wrap_tmp / "second" / "bloo.txt").touch()

        obj = Walker(DootTaskSpec.from_dict({"name" : "basic", "exts" : [".txt"], "recursive": False}))

        count = 0
        for sub in obj.build():
            count += 1
            assert(isinstance(sub, DootTaskSpec))
            assert(str(sub.name) in ["default::basic.$head$"])

        assert(count == 1)


    def test_subtask_specify_ctor(self, wrap_tmp):
        (wrap_tmp / "first").mkdir()
        (wrap_tmp / "first" / "blah.txt").touch()
        (wrap_tmp / "second").mkdir()
        (wrap_tmp / "second" / "bloo.txt").touch()

        obj = Walker(DootTaskSpec.from_dict({"name" : "basic", "exts" : [".txt"], "recursive": False}))

        count = 0
        for sub in obj.build():
            count += 1
            assert(isinstance(sub, DootTaskSpec))
            assert(str(sub.name) in ["default::basic.$head$"])

        assert(count == 1)


    def test_non_existing_target(self, wrap_tmp, caplog):
        (wrap_tmp / "first").mkdir()
        (wrap_tmp / "first" / "blah.txt").touch()
        (wrap_tmp / "second").mkdir()
        (wrap_tmp / "second" / "bloo.txt").touch()

        obj = Walker(DootTaskSpec.from_dict({
            "name"        : "basic",
            "exts"        : [".txt"],
            "recursive"   : False,
            "roots"       : [pl.Path() / "aweg" ],
                                                      }))
        count = 0
        for sub in obj.build():
            count += 1
            assert(isinstance(sub, DootTaskSpec))
            assert(str(sub.name) in ["default::basic.$head$"])

        assert(count == 1)
        assert("Walker Missing Root: aweg" in caplog.messages)
