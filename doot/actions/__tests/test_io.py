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
from doot.task.core.task import DootTask
from doot.actions.core.action import DootBaseAction


class TestBaseAction:

    def test_initial(self):
        action = DootBaseAction()
        assert(isinstance(action, DootBaseAction))

    def test_call_action(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        action = DootBaseAction()
        state  = { "count" : 0  }
        spec   = mocker.Mock(spec=doot.structs.ActionSpec)
        spec.args = []
        result = action(spec, state)
        assert(result['count'] == 1)
        assert("Base Action Called: 0" in caplog.messages)


    @pytest.mark.skip
    def test_todo(self):
        pass
