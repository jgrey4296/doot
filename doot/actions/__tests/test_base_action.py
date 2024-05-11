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
doot._test_setup()

import doot._abstract
import doot.structs
from doot.task.base_task import DootTask
from doot.actions.base_action import DootBaseAction

class TestBaseAction:

    def test_initial(self):
        action = DootBaseAction()
        assert(isinstance(action, DootBaseAction))

    def test_call_action(self, caplog, mocker):
        action = DootBaseAction()
        state  = { "count" : 0  }
        spec   = mocker.Mock(spec=doot.structs.ActionSpec)
        spec.args = []
        result = action(spec, state)
        assert(result['count'] == 1)
        assert("Base Action Called: 0" in caplog.messages)
