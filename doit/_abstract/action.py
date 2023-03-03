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

class BaseAction:
    """Base class for all actions"""

    # must implement:
    # def execute(self, out=None, err=None)

    @staticmethod
    def _prepare_kwargs(task, func, args, kwargs):
        """
        Prepare keyword arguments (targets, dependencies, changed,
        cmd line options)
        Inspect python callable and add missing arguments:
        - that the callable expects
        - have not been passed (as a regular arg or as keyword arg)
        - are available internally through the task object
        """
        # Return just what was passed in task generator
        # dictionary if the task isn't available
        if not task:
            return kwargs

        func_sig = inspect.signature(func)
        sig_params = func_sig.parameters.values()
        func_has_kwargs = any(p.kind == p.VAR_KEYWORD for p in sig_params)

        # use task meta information as extra_args
        meta_args = {
            'task': lambda: task,
            'targets': lambda: list(task.targets),
            'dependencies': lambda: list(task.file_dep),
            'changed': lambda: list(task.dep_changed),
        }

        # start with dict passed together on action definition
        kwargs = kwargs.copy()
        bound_args = func_sig.bind_partial(*args)

        # add meta_args
        for key in meta_args.keys():
            # check key is a positional parameter
            if key in func_sig.parameters:
                sig_param = func_sig.parameters[key]

                # it is forbidden to use default values for this arguments
                # because the user might be unaware of this magic.
                if (sig_param.default != sig_param.empty):
                    msg = (f"Task {task.name}, action {func.__name__}():"
                           f"The argument '{key}' is not allowed to have "
                           "a default value (reserved by doit)")
                    raise InvalidTask(msg)

                # if value not taken from position parameter
                if key not in bound_args.arguments:
                    kwargs[key] = meta_args[key]()

        # add tasks parameter options
        opt_args = dict(task.options)
        if task.pos_arg is not None:
            opt_args[task.pos_arg] = task.pos_arg_val

        for key in opt_args.keys():
            # check key is a positional parameter
            if key in func_sig.parameters:
                # if value not taken from position parameter
                if key not in bound_args.arguments:
                    kwargs[key] = opt_args[key]

            # if function has **kwargs include extra_arg on it
            elif func_has_kwargs and key not in kwargs:
                kwargs[key] = opt_args[key]
        return kwargs






def create_action(action, task_ref, param_name):
    """
    Create action using proper constructor based on the parameter type

    @param action: Action to be created
    @type action: L{BaseAction} subclass object, str, tuple or callable
    @param task_ref: Task object this action belongs to
    @param param_name: str, name of task param. i.e actions, teardown, clean
    @raise InvalidTask: If action parameter type isn't valid
    """
    if isinstance(action, BaseAction):
        action.task = task_ref
        return action

    if isinstance(action, str):
        return CmdAction(action, task_ref, shell=True)

    if isinstance(action, list):
        return CmdAction(action, task_ref, shell=False)

    if isinstance(action, tuple):
        if len(action) > 3:
            msg = "Task '{}': invalid '{}' tuple length. got: {!r} {}".format(
                task_ref.name, param_name, action, type(action))
            raise InvalidTask(msg)
        py_callable, args, kwargs = (list(action) + [None] * (3 - len(action)))
        return PythonAction(py_callable, args, kwargs, task_ref)

    if hasattr(action, '__call__'):
        return PythonAction(action, task=task_ref)

    msg = "Task '{}': invalid '{}' type. got: {!r} {}".format(
        task_ref.name, param_name, action, type(action))
    raise InvalidTask(msg)
