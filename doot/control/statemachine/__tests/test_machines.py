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
from doot.control.statemachine import task_machine as tm
from doot.enums import TaskStatus_e


logging = logmod.root


class TestTaskStateMachine:

    @pytest.fixture(scope="function")
    def model(self):
        return tm.TaskTrackMachine(model=tm.TaskTrackModel())

    def test_sanity(self, model):
        assert(True is True)
        assert(model.current_state.value is TaskStatus_e.NAMED)


    def test_setup_transition(self):
        assert(True is True)
        model = tm.TaskTrackMachine(model=tm.TaskTrackModel())
        assert(model.current_state.value is TaskStatus_e.NAMED)
        model.send("progress")
        assert(model.current_state.value is TaskStatus_e.DECLARED)
        model.send("progress")
        assert(model.current_state.value is TaskStatus_e.DEFINED)
        model.send("progress")
        assert(model.current_state.value is TaskStatus_e.INIT)
        model.send("progress")
        assert(model.current_state.value is TaskStatus_e.WAIT)
        model.send("progress")
        assert(model.current_state.value is TaskStatus_e.READY)


    @pytest.mark.skip
    def test_todo(self):
        pass
