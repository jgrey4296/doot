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
import os

logging = logmod.root

import pytest

import tomler
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
        action = DootBaseAction("example-spec")
        assert(isinstance(action, DootBaseAction))
        assert(action.spec == "example-spec")

    def test_call_action(self, caplog):
        action = DootBaseAction("example-spec")
        state  = { "count" : 0  }
        result = action(state)
        assert(result['count'] == 1)
        assert("Action Spec: example-spec" in caplog.messages)
