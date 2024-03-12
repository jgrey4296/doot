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
from doot import structs

class TestActionSpec:

    def test_initial(self):
        obj = structs.DootActionSpec()
        assert(isinstance(obj, structs.DootActionSpec))


    def test_build_from_dict(self):
        obj = structs.DootActionSpec.build({"do":"test"})
        assert(isinstance(obj, structs.DootActionSpec))
        assert(obj.do == "test")


    def test_build_from_list(self):
        obj = structs.DootActionSpec.build({"do":"test"})
        assert(isinstance(obj, structs.DootActionSpec))
        assert(obj.do == "test")


    def test_build_nop(self):
        obj = structs.DootActionSpec.build([])
        obj2 = structs.DootActionSpec.build(obj)
        assert(obj is obj2)


    def test_call(self, mocker):
        fun_mock = mocker.Mock()
        obj = structs.DootActionSpec(fun=fun_mock)

        obj({})
        fun_mock.assert_called_once()


    def test_set_function(self):
        pass
