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

from doit.abstract.cmd_base import TaskLoader2

class NamespaceTaskLoader(TaskLoader2):
    """Implementation of a loader of tasks from an abstract namespace.

    A namespace is simply a dictionary to objects like functions and
    objects. See the derived classes for some concrete namespace types.
    """
    def __init__(self):
        super().__init__()
        self.namespace = None

    def load_doit_config(self):
        return loader.load_doit_config(self.namespace)

    def load_tasks(self, cmd, pos_args):
        tasks = loader.load_tasks(
            self.namespace, self.cmd_names, allow_delayed=cmd.execute_tasks,
            args=pos_args, config=self.config, task_opts=self.task_opts)

        # Add task options from config, if present
        if self.config is not None:
            for task in tasks:
                task_stanza = 'task:' + task.name
                if task_stanza in self.config:
                    task.cfg_values = self.config[task_stanza]

        # add values from API run_tasks() usage
        if self.task_opts is not None:
            for task in tasks:
                if self.task_opts and task.name in self.task_opts:
                    task.cfg_values = self.task_opts[task.name]
                    if task.pos_arg and task.pos_arg in task.cfg_values:
                        task.pos_arg_val = task.cfg_values[task.pos_arg]
        return tasks
