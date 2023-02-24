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


from doot.utils.task_namer import task_namer

import sys

class DelayedMixin:
    """
    Delays Subtask generation until the main task is executed

    """
    _delayed_task_names = None

    @property
    def delayed_name(self):
        return task_namer("delayed", self.fullname, private=True)

    @property
    def calc_dep_taskname(self):
        return task_namer(self.delayed_name, "calc_delayed_tasks", private=True)

    @property
    def delayed_subtask_name(self):
        return task_namer(self.delayed_name, "subtask_gen", private=True)

    def _build_task(self):
        task = super()._build_task()
        if task is None:
            return None

        task.name = self.delayed_name
        task.update_deps({ "calc_dep" : [ self.calc_dep_taskname ]})
        return task

    def build(self, **kwargs):
        logging.debug("Wrapping Task for delay sequencing: %s", self.fullname)
        yield { # Simple Wrapper to sequence properly
            "head_task" : True,
            "basename"  : self.fullname,
            "actions"   : None,
            "task_dep"  : [
                # The delayed subtasks generator
                self.delayed_subtask_name,
                # The actual task this wraps
                self.delayed_name,
            ],
        }
        yield from super().build(**kwargs)
        yield self._build_delayed_deps

    def _build_delayed_deps(self):
        return { # The calc_deps subtask for main
            "basename": self.calc_dep_taskname,
            "actions": [ self.delayed_tasknames_action ],
        }

    def delayed_tasknames_action(self, task):
        logging.debug("Retrieving Delayed Task Names: %s : %s", task.name, self._delayed_task_names)
        task_names = self._delayed_task_names or []
        return { "task_dep": task_names[:] }

    def _build_subs(self):
        return []

    def _build_delayed(self, **kwargs):
        logging.debug("Delayed Tasks now building : %s", self.fullname)
        self._delayed_task_names = []
        for task in super(DelayedMixin, self)._build_subs():
            task['basename'] = task_namer(self.delayed_name, task["name"])
            del task['name']
            self._delayed_task_names.append(task['basename'])
            yield task

        logging.debug("There are %s newly delayed tasks", len(self._delayed_task_names))
