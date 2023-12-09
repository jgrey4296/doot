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
from doot import structs
import doot.constants

# caplog
# mocker.patch | patch.object | patch.multiple | patch.dict | stopall | stop | spy | stub
# pytest.mark.filterwarnings
# pytest.parameterize
# pytest.skip | skipif | xfail
# with pytest.deprecated_call
# with pytest.raises
# with pytest.warns(warntype)

class TestActionSpec:

    def test_initial(self):
        obj = structs.DootActionSpec()
        assert(isinstance(obj, structs.DootActionSpec))


    def test_call(self, mocker):
        fun_mock = mocker.Mock()
        obj = structs.DootActionSpec(fun=fun_mock)

        obj({})
        fun_mock.assert_called_once()
