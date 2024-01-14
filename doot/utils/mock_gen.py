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

from unittest.mock import PropertyMock, MagicMock, create_autospec
from importlib.metadata import EntryPoint
import tomlguard
from doot import structs
from doot._abstract import Task_i, Job_i, TaskBase_i, Command_i, TaskTracker_i, TaskRunner_i

def _add_prop(m, name, val):
    setattr(type(m), name, PropertyMock(return_value=val))

def task_network(tasks:dict):
    built = []
    for name, [pre, post] in tasks.items():
        current = mock_task_spec(name, pre=pre, post=post)
        built.append(current)

    return built



def mock_task(name, spec=None, actions:int=1, **kwargs):
    task_m = MagicMock(spec=Task_i,
                       depends_on=[],
                       required_for=[],
                       name=name,
                       state={},
                       **kwargs)
    task_m.spec = spec or mock_task_spec(name=name, action_count=actions)
    _add_prop(task_m, "name", name)
    _add_prop(task_m, "actions", task_m.spec.actions)
    return task_m

def mock_job(name, pre=None, post=None, spec=None, **kwargs):
    task_m = MagicMock(spec=Job_i,
                       depends_on=[],
                       required_for=[],
                       name=name,
                       **kwargs)
    _add_prop(task_m, "name", name)
    task_m.spec = spec or mock_task_spec(name=name)
    return task_m

def mock_task_spec(name="mockSpec", pre=None, post=None, action_count=1, extra=None,  **kwargs):
    extra = extra or {}
    if "sleep" not in extra:
        extra['sleep'] = 0.1
    spec_m = MagicMock(structs.DootTaskSpec(name=name),
                       actions=mock_action_specs(num=action_count),
                       extra=tomlguard.TomlGuard(extra),
                       priority=10,
                       queue_behaviour="default",
                       depends_on=pre or [],
                       required_for=post or [],
                       print_levels=tomlguard.TomlGuard({}),
                        )
    spec_m.name = name
    return spec_m

def mock_action_specs(num=1) -> list:
    results = []
    for x in range(num):
        action_spec_m = MagicMock(spec=structs.DootActionSpec(),
                                  args=[],
                                  kwargs=tomlguard.TomlGuard())
        type(action_spec_m).__call__ = MagicMock(return_value=None)
        results.append(action_spec_m)

    return results

def mock_parse_cmd(name="cmd", params=None):
    """ Build a mock command with cli params """
    cmd_mock = MagicMock(spec=Command_i, name=name)
    _add_prop(cmd_mock, "name", name)
    _add_prop(cmd_mock, "param_specs", [mock_param_spec("help", False, type=bool)] + (params or []))
    return cmd_mock

def mock_parse_task(params=None, ctor_params=None):
    """ Build a mock Task Spec, with spec defined cli params, and ctor defined cli params  """
    task_ctor_mock       = mock_task_ctor(params=ctor_params)
    task_ctor_ref_mock   = mock_code_ref(returns=task_ctor_mock)
    task_mock            = mock_task_spec(extra={"cli": params})
    task_mock.ctor       = task_ctor_ref_mock
    return task_mock

def mock_entry_point(name="basic", value=None):
    m = MagicMock(spec=EntryPoint)
    _add_prop(m, "name", name)
    _add_prop(m, "value", name)
    m.load.return_value = value
    return m

def mock_task_ctor(name="APretendClass", module="pretend", params=None):
    mock_ctor = MagicMock(spec=TaskBase_i)
    _add_prop(mock_ctor, "name", name)
    _add_prop(mock_ctor, "param_specs", params or [])
    mock_ctor.__module__ = module
    mock_ctor.__name__   = name
    return mock_ctor

def mock_code_ref(returns=None):
    code_ref_m  = MagicMock(spec=structs.DootCodeReference())
    code_ref_m.try_import.return_value  = returns
    return code_ref_m

def mock_param_spec(name, val, type=Any):
    m = MagicMock(spec=structs.DootParamSpec(name, type), default=val, positional=False, prefix="-")

    return m


def mock_tracker(tasks):
    tracker_m        = MagicMock(spec=TaskTracker_i)
    local_tasks      = tasks[:]
    def simple_pop():
        if bool(local_tasks):
            return local_tasks.pop()
        return None

    tracker_m.next_for = simple_pop
    tracker_m.__bool__ = lambda x: bool(local_tasks)
    return tracker_m
