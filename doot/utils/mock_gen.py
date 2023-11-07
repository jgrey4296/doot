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

from doot import structs
from doot._abstract import Task_i

def mock_task_spec(mocker):
    pass

def mock_action_spec(mocker):
    pass

def mock_tracker_and_reporter(mocker):
    pass

def mock_task(mocker, name, pre=None, post=None):
    mock_task                      = mocker.MagicMock(spec=Task_i)
    mock_task.name                 = name
    mock_task.spec                 = mocker.MagicMock(spec=structs.DootTaskSpec)
    mock_task.spec.priority        = 0

    runs_after                     = pre or mocker.PropertyMock()
    runs_before                    = post or mocker.PropertyMock()
    type(mock_task).runs_after     = runs_after
    type(mock_task).runs_before    = runs_before
    return mock_task, runs_after, runs_before



"""


"""
