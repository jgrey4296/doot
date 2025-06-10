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

from jgdv.structs.strang import CodeReference
from jgdv._abstract.protocols import SpecStruct_p
import doot
from ..action_spec import ActionSpec

class TestActionSpec:

    def test_initial(self):
        obj = ActionSpec()
        assert(isinstance(obj, ActionSpec))

    def test_build_from_dict(self):
        obj = ActionSpec.build({"do":"basic"})
        assert(isinstance(obj, ActionSpec))
        assert(str(obj.do) == CodeReference(doot.aliases.action['basic']))

    def test_build_from_list(self):
        obj = ActionSpec.build({"do":"basic"})
        assert(isinstance(obj, ActionSpec))
        assert(str(obj.do) == CodeReference(doot.aliases.action['basic']))

    def test_build_nop(self):
        obj = ActionSpec.build([])
        obj2 = ActionSpec.build(obj)
        assert(obj is obj2)

    def test_build_with_args(self):
        obj = ActionSpec(do="log", args=[1,2,3])
        assert(obj.args == [1,2,3])
        assert(isinstance(obj, SpecStruct_p))

    def test_call(self, mocker):
        fun_mock = mocker.Mock()
        obj = ActionSpec(fun=fun_mock)

        obj({})
        fun_mock.assert_called_once()

    def test_set_function(self):
        obj = ActionSpec.build({"do":"basic"})
        assert(obj.fun is None)
        obj.set_function(fun=lambda *args: 2)
        assert(obj.fun is not None)
