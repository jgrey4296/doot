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

from doot.workflow.structs.action_spec import ActionSpec
from doot.workflow.task import DootTask
from doot.workflow.actions._action import DootBaseAction

from jgdv.logging import LogLevel_e

class TestBaseAction:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_initial(self):
        action = DootBaseAction()
        assert(isinstance(action, DootBaseAction))

    def test_logging(self, caplog):
        with caplog.at_level(logmod.NOTSET, logger="testing"):
            logging = logmod.getLogger("testing")
            logging.warning("blah")
            assert("blah" in caplog.messages)

    def test_call_action(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger=doot.report.log.name)
        action = DootBaseAction()
        state  = { "count" : 0  }
        spec   = mocker.Mock(spec=ActionSpec)
        spec.args = []
        result = action(spec, state)
        assert(result['count'] == 1)
        assert("Base Action Called: 0" in caplog.messages)

    @pytest.mark.skip
    def test_todo(self):
        pass
