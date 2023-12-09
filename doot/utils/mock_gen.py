#!/usr/bin/env python3
"""
Some utility functions to more easily setup mocks

See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import tomlguard
from doot import structs
from doot._abstract import Task_i, Tasker_i

def mock_tasker_spec(mocker):
    tasker_m                                     = mocker.MagicMock(spec=Tasker_i)
    tasker_m.spec                                = mocker.MagicMock(spec=structs.DootTaskSpec)
    type(tasker_m.spec).extra                    = tomlguard.TomlGuard()
    type(tasker_m.spec).print_levels             = tomlguard.TomlGuard()
    tasker_m.spec.actions                        = []
    return tasker_m

def mock_task_spec(mocker, action_count=0):
    task_m                                     = mocker.MagicMock(spec=Task_i)
    task_m.spec                                = mocker.MagicMock(spec=structs.DootTaskSpec)
    type(task_m.spec).extra                    = tomlguard.TomlGuard()
    type(task_m.spec).print_levels             = tomlguard.TomlGuard()
    task_m.state = {}
    type(task_m).actions                      = mocker.PropertyMock(return_value=mock_action_spec(mocker, num=action_count))
    return task_m


def mock_action_spec(mocker, num=1) -> list:
    results = []
    for x in range(num):
        action_spec_m                                = mocker.MagicMock(spec=structs.DootActionSpec)
        type(action_spec_m).args                     = mocker.PropertyMock(return_value=[])
        type(action_spec_m).kwargs                   = tomlguard.TomlGuard()
        type(action_spec_m).__call__                 = mocker.MagicMock(return_value=None)
        results.append(action_spec_m)

    return results

def mock_tracker_and_reporter(mocker):
    pass

def mock_task(mocker, name, pre=None, post=None):
    mock_task                       = mocker.MagicMock(spec=Task_i)
    mock_task.name                  = name
    mock_task.spec                  = mocker.MagicMock(spec=structs.DootTaskSpec)
    mock_task.spec.priority         = 0

    depends_on                      = pre or mocker.PropertyMock()
    required_for                    = post or mocker.PropertyMock()
    type(mock_task).depends_on      = depends_on
    type(mock_task).required_for    = required_for
    return mock_task, depends_on, required_for



"""


"""


def mock_parse_cmd(mocker, params=None):
    params                     = params or []
    cmd_mock                   = mocker.MagicMock()
    type(cmd_mock).param_specs = mocker.PropertyMock(return_value=params)
    return cmd_mock

def mock_parse_task(mocker, params=None):
    params                      = params or []
    task_mock                   = mocker.MagicMock()
    type(task_mock).param_specs = mocker.PropertyMock(return_value=params)
    return task_mock
