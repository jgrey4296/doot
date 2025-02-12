#!/usr/bin/env python3
"""
Some utility functions to more easily setup mocks


"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
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
from importlib.metadata import EntryPoint
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from unittest.mock import MagicMock, PropertyMock, create_autospec
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
from doot import structs
from doot._abstract import (Command_i, Job_i, Task_i, TaskRunner_i,
                            TaskTracker_i)
from doot.enums import QueueMeta_e

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

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
                       name=name,
                       state={},
                       **kwargs)
    task_m.spec = spec or mock_task_spec(name=name, action_count=actions)
    _add_prop(task_m, "name", structs.TaskName(name))
    _add_prop(task_m, "actions", task_m.spec.actions)
    return task_m

def mock_job(name, pre=None, post=None, spec=None, **kwargs):
    task_m = MagicMock(spec=Job_i,
                       name=name,
                       state={},
                       **kwargs)
    _add_prop(task_m, "name", name)
    task_m.spec = spec or mock_task_spec(name=name)
    return task_m

def mock_task_spec(name="agroup::mockSpec", pre=None, post=None, action_count=1, extra=None,  **kwargs):
    extra = extra or {}
    if "sleep" not in extra:
        extra['sleep'] = 0.1
    spec_m = MagicMock(structs.TaskSpec(name=name),
                       actions=mock_action_specs(num=action_count),
                       extra=ChainGuard(extra),
                       priority=10,
                       queue_behaviour=QueueMeta_e.default,
                       depends_on=pre or [],
                       required_for=post or [],
                       setup=[],
                       cleanup=[],
                       )
    spec_m.name = structs.TaskName(name)
    return spec_m

def mock_action_specs(num=1) -> list:
    results = []
    for x in range(num):
        action_spec_m = MagicMock(spec=structs.ActionSpec(),
                                  args=[],
                                  kwargs=ChainGuard())
        type(action_spec_m).__call__ = MagicMock(return_value=None)
        results.append(action_spec_m)

    return results

def mock_entry_point(name="basic", value=None):
    m = MagicMock(spec=EntryPoint)
    _add_prop(m, "name", name)
    _add_prop(m, "value", value)
    m.load = MagicMock(return_value=value)
    return m

def mock_task_ctor(name="APretendClass", module="pretend", params=None):

    class MockedSubClass(Task_i):

        def __new__(cls, *args, **kwargs):
            m = mock.Mock(spec=cls)
            _add_prop(mock_ctor, "name", name)
            _add_prop(mock_ctor, "param_specs", params or [])
            return m

        @classmethod
        @property
        def param_specs(cls):
            return params or []

    mock_ctor = MockedSubClass
    mock_ctor.__module__ = module
    mock_ctor.__name__   = name
    return mock_ctor

def mock_code_ref(returns=None):
    code_ref_m  = MagicMock(spec=structs.CodeReference())
    code_ref_m.__call__ = MagicMock(return_value=returns)
    return code_ref_m

def mock_param_spec(name, val, type=Any):
    m = MagicMock(spec=structs.ParamSpec(name=name, type=type), default=val, prefix="-")

    return m

def mock_tracker(tasks):
    tracker_m        = MagicMock(spec=TaskTracker_i)
    local_tasks      = tasks[:]

    def simple_pop():
        if bool(local_tasks):
            return local_tasks.pop()
        return None

    tracker_m.next_for = simple_pop
    return tracker_m
