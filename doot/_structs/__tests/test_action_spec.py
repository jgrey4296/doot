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

import tomlguard
import doot
doot._test_setup()
from doot._structs.action_spec import DootActionSpec

class TestActionSpec:

    def test_initial(self):
        obj = DootActionSpec()
        assert(isinstance(obj, DootActionSpec))

    def test_build_from_dict(self):
        obj = DootActionSpec.build({"do":"test"})
        assert(isinstance(obj, DootActionSpec))
        assert(obj.do == "test")

    def test_build_from_list(self):
        obj = DootActionSpec.build({"do":"test"})
        assert(isinstance(obj, DootActionSpec))
        assert(obj.do == "test")

    def test_build_nop(self):
        obj = DootActionSpec.build([])
        obj2 = DootActionSpec.build(obj)
        assert(obj is obj2)

    def test_call(self, mocker):
        fun_mock = mocker.Mock()
        obj = DootActionSpec(fun=fun_mock)

        obj({})
        fun_mock.assert_called_once()

    @pytest.mark.xfail
    def test_set_function(self):
        raise NotImplementedError()
