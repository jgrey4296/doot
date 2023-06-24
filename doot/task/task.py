#!/usr/bin/env python3
"""
Extension to Doit's Task and Actions,
To allow:
1) returning an Action from an Action and using it
2) only calling a CmdAction's python callable once
3) putting any extraneous kwargs in a task dict into the `meta` dict automatically
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

import functools
import pdb
import sys
from io import StringIO

import doot
from doot._abstract.task import Task_i
from doot.actions.py_cmd_action import DootPyAction


class DootTask(Task_i):
    """
    Extension of doit.Task to allow returning an Action from an action,
    making a task's `execute` a stack of actions instead of a list
    """
    action_builder = DootPyAction.build
    name_splitter = re.compile(r":+|\.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **{x:y for x,y in kwargs.items() if x in Task.valid_attr or x == 'loader'})
        if self.meta is None:
            self.meta = dict()
        self.meta.update({x:y for x,y in kwargs.items() if x not in Task.valid_attr})

    @property
    def actions(self):
        """lazy creation of action instances"""
        if self._action_instances is None:
            builder = self.action_builder
            self._action_instances = list(map(lambda x: builder(x, self, 'actions'), self._actions))
        return self._action_instances

    def execute(self, stream):
        """Executes the task.
        @return failure: see CmdAction.execute
        """
        logging.debug("Executing Task: %s", self.name)
        self.executed = True
        self.init_options()
        task_stdout, task_stderr = stream._get_out_err(self.verbosity)
        actions = self.actions[:]
        actions.reverse()
        while bool(actions):
            action = actions.pop()
            logging.debug("%s Task Action: %s", self.name, action)
            if action.task is None:
                action.task = self
            action_return = action.execute(task_stdout, task_stderr)
            match action_return:
                case BaseFail():
                    return action_return
                case BaseAction():
                    actions.append(action_return)
                case [*args] if all(isinstance(x, BaseAction) for x in args):
                    actions += args
                case _:
                    self.result = action.result
                    self.values.update(action.values)

    def name_parts(self):
        return self.name_splitter.split(self.name)

    def report(self, template, list_deps) -> str:
        """print a single task"""
        line_data = {'name': self.name, 'doc': self.doc}
        results = []
        results.append("\t" + template.format(**line_data))

        if list_deps:
            for dep in self.task_dep:
                results.append(f"\t\t -(t)- {dep}")
            for dep in self.file_dep:
                results.append(f"\t\t -(f)- {dep}")

        return "\n".join(results)
