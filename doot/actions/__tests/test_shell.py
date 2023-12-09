#!/usr/bin/env python3
"""

"""
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
from dataclasses import fields
import warnings
import os

logging = logmod.root

import pytest

import doot
import doot._abstract
import doot.structs
import doot.constants
from doot.task.base_task import DootTask
from doot.actions.base_action import DootBaseAction

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

class TestBaseAction:

    def test_initial(self):
        action = DootBaseAction()
        assert(isinstance(action, DootBaseAction))

    def test_call_action(self, caplog, mocker):
        action = DootBaseAction()
        state  = { "count" : 0  }
        spec   = mocker.Mock(spec=doot.structs.DootActionSpec)
        spec.args = []
        result = action(spec, state)
        assert(result['count'] == 1)
        assert("Base Action Called: 0" in caplog.messages)
