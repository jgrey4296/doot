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

matcher_ref        = DootCodeReference.from_str("doot.task.base_tasker:DootTasker").add_mixins("doot.mixins.tasker.matcher:MatcherMixin")
MatcherBuilder     = matcher_ref.try_import()

class SimpleMatcher(MatcherBuilder):

    def _build_subs(self) -> Generator[DootTaskSpec]:
        yield self._build_subtask(0, "first")
        yield self._build_subtask(0, "second")


class TestMatcher:

    def test_initial(self):
        obj = MatcherBuilder(DootTaskSpec.from_dict({"name" : "test::basic"}))
        assert(isinstance(obj, TaskBase_i))
