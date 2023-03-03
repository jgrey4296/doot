#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

def check_tasks_exist(tasks, name_list, skip_wildcard=False):
    """check task exist"""
    if not name_list:
        return
    for task_name in name_list:
        if skip_wildcard and '*' in task_name:
            continue
        if task_name not in tasks:
            msg = "'%s' is not a task."
            raise InvalidCommand(msg % task_name)


# this is used by commands that do not execute tasks (forget, auto...)
def tasks_and_deps_iter(tasks, sel_tasks, yield_duplicates=False):
    """iterator of select_tasks and its dependencies

    @param tasks (dict - Task)
    @param sel_tasks(list - str)
    """
    processed = set()  # str - task name
    to_process = deque(sel_tasks)  # str - task name
    # get initial task
    while to_process:
        task = tasks[to_process.popleft()]
        processed.add(task.name)
        yield task
        # FIXME this does not take calc_dep into account
        for task_dep in task.task_dep + task.setup_tasks:
            if (task_dep not in processed) and (task_dep not in to_process):
                to_process.append(task_dep)
            elif yield_duplicates:
                yield tasks[task_dep]


def subtasks_iter(tasks, task):
    """find all subtasks for a given task
    @param tasks (dict - Task)
    @param task (Task)
    """
    for name in task.task_dep:
        dep = tasks[name]
        if dep.subtask_of == task.name:
            yield dep


def get_loader(config, task_loader=None, cmds=None):
    """get task loader and configure it

    :param config: (dict) the whole config from INI
    :param task_loader: a TaskLoader class
    :param cmds: dict of available commands
    """
    config = config if config else {}
    loader = None
    if task_loader:
        loader = task_loader  # task_loader set from the API
    else:
        global_config = config.get('GLOBAL', {})
        if 'loader' in global_config:
            # a plugin loader
            loader_name = global_config['loader']
            plugins = PluginDict()
            plugins.add_plugins(config, 'LOADER')
            loader = plugins.get_plugin(loader_name)()

    if not loader:
        loader = DodoTaskLoader()  # default loader

    if cmds:
        loader.cmd_names = list(sorted(cmds.keys()))
    loader.config = config
    return loader
