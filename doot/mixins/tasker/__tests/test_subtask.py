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

# caplog
# mocker.patch | patch.object | patch.multiple | patch.dict | stopall | stop | spy | stub
# pytest.mark.filterwarnings
# pytest.parameterize
# pytest.skip | skipif | xfail
# with pytest.deprecated_call
# with pytest.raises
# with pytest.warns(warntype)

import doot
from doot.enums import TaskFlags
from doot.structs import DootTaskSpec, TaskStub
from doot.task.base_tasker import DootTasker
from doot.mixins.tasker.subtask import SubMixin
import doot._abstract

class SimpleSubTasker(SubMixin, DootTasker):

    def build(self, **kwargs):
        head = self._build_head()
        for sub in self._build_subs():
            head.depends_on.append(sub.name)
            yield sub

        yield head

    def _build_subs(self):
        yield DootTaskSpec(name=self.fullname.subtask("first"))
        yield DootTaskSpec(name=self.fullname.subtask("second"))

class SetupTearDownTasker(SimpleSubTasker):

    def build(self, **kwargs):
        head     = self._build_head()
        setup    = DootTaskSpec(name=self.fullname.subtask("setup"))
        teardown = DootTaskSpec(name=self.fullname.subtask("teardown"))
        head.depends_on.append(teardown)
        head.depends_on.append(setup)

        for sub in super()._build_subs():
            sub.depends_on.append(setup.name)
            teardown.depends_on.append(sub.name)
            yield sub

        yield setup
        yield teardown
        yield head


class TestSubtasks:

    def test_initial(self):
        obj = SimpleSubTasker(DootTaskSpec.from_dict({"name": "simple"}))
        assert(isinstance(obj, doot._abstract.TaskBase_i))


    def test_builds_task(self):
        obj   = SimpleSubTasker(DootTaskSpec.from_dict({"name": "simple"}))
        tasks = list(obj.build())
        assert(len(tasks) == 3)
        names = [str(x.name) for x in tasks]
        assert("default::simple.$head$" in names)
        assert("default::simple.first" in names)
        assert("default::simple.second" in names)


    def test_setup_teardown(self):
        obj   = SetupTearDownTasker(DootTaskSpec.from_dict({"name": "simple"}))
        tasks = list(obj.build())
        assert(len(tasks) == 5)
        names = [str(x.name) for x in tasks]
        assert("default::simple.$head$" in names)
        assert("default::simple.setup" in names)
        assert("default::simple.teardown" in names)
        assert("default::simple.first" in names)
        assert("default::simple.second" in names)
