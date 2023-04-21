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
from doit.task import Task
from doit.exceptions import BaseFail, TaskError, TaskFailed, InvalidTask
from doit.action import BaseAction, CmdAction, PythonAction, Writer

class DootCmdAction(CmdAction):
    """
    CmdAction that doesn't call it's python callable multiple times
    (for a single call of `execute`)
    """

    def __str__(self):
        return f"Cmd: {self._action}"

    @property
    def action(self):
        match self._action:
            case str() | list():
                return self._action
            case [ref, args, kw]:
                # action can be a callable that returns a string command
                kwargs = self._prepare_kwargs(self.task, ref, args, kw)
                return ref(*args, **kwargs)
            case _ as ref:
                args, kw = (), {}
                kwargs = self._prepare_kwargs(self.task, ref, args, kw)
                return ref(*args, **kwargs)

    def expand_action(self):
        """Expand action using task meta informations if action is a string.
        Convert `Path` elements to `str` if action is a list.
        @returns: string -> expanded string if action is a string
                    list - string -> expanded list of command elements
        """
        action_prepped = self.action

        if not self.task:
            return action_prepped

        if isinstance(action_prepped, list):
            # cant expand keywords if action is a list of strings
            action = []
            for element in action_prepped:
                if isinstance(element, str):
                    action.append(element)
                elif isinstance(element, pl.PurePath):
                    action.append(str(element))
                else:
                    msg = ("%s. CmdAction element must be a str "
                            "or Path from pathlib. Got '%r' (%s)")
                    raise InvalidTask(msg % (self.task.name, element, type(element)))
            return action

        subs_dict = {
            'targets'      : " ".join(self.task.targets),
            'dependencies' : " ".join(self.task.file_dep),
        }

        # dep_changed is set on get_status()
        # Some commands (like `clean` also uses expand_args but do not
        # uses get_status, so `changed` is not available.
        if self.task.dep_changed is not None:
            subs_dict['changed'] = " ".join(self.task.dep_changed)

        # task option parameters
        subs_dict.update(self.task.options)
        # convert positional parameters from list space-separated string
        if self.task.pos_arg:
            if self.task.pos_arg_val:
                pos_val = ' '.join(self.task.pos_arg_val)
            else:
                pos_val = ''
            subs_dict[self.task.pos_arg] = pos_val

        if self.STRING_FORMAT == 'old':
            return action_prepped % subs_dict
        elif self.STRING_FORMAT == 'new':
            return action_prepped.format(**subs_dict)
        else:
            assert self.STRING_FORMAT == 'both'
            return action_prepped.format(**subs_dict) % subs_dict

class DootPyActionExt(PythonAction):
    """
    Python Action with a `build` static method instead of doit.action.create_action
    and refactored `execute` to allow returning Actions from actions
    """

    @staticmethod
    def build(action, task_ref, param_name) -> BaseAction:
        """
        Create action using proper constructor based on the parameter type

        @param action: Action to be created
        @type action: L{BaseAction} subclass object, str, tuple or callable
        @param task_ref: Task object this action belongs to
        @param param_name: str, name of task param. i.e actions, teardown, clean
        @raise InvalidTask: If action parameter type isn't valid
        """
        result = None
        match action:
            case BaseAction():
                action.task = task_ref
                result = action
            case str():
                result = DootCmdAction(action, task_ref, shell=True)
            case list():
                reuslt = DootCmdAction(action, task_ref, shell=False)
            case tuple() if 1 <= len(action) < 4:
                py_callable, args, kwargs = (list(action) + [None] * (3 - len(action)))
                result = DootPyActionExt(py_callable, args, kwargs, task_ref)
            case _ if hasattr(action, '__call__'):
                result = DootPyActionExt(action, task=task_ref)
            case _:
                msg = "Task '{}': invalid '{}' type. got: {!r} {}".format(
                task_ref.name, param_name, action, type(action))
                raise InvalidTask(msg)

        return result

    def execute(self, out=None, err=None):
        """Execute command action

        both stdout and stderr from the command are captured and saved
        on self.out/err. Real time output is controlled by parameters
        @param out: None - no real time output
                    a file like object (has write method)
        @param err: idem

        @return failure: see CmdAction.execute
        """
        capture_io = self.task.io.capture if self.task else True
        # execute action / callable
        old_stdout, old_stderr = sys.stdout, sys.stderr

        if capture_io:
            output, errput = self._capture_io(out, err)
        else:
            if out:
                sys.stdout = out
            if err:
                sys.stderr = err

        try:
            kwargs = self._prepare_kwargs()
            returned_value = self.py_callable(*self.args, **kwargs)
            return self._handle_return(returned_value, self.py_callable)
        except Exception as exception:
            if self.pm_pdb:  # pragma: no cover
                # start post-mortem debugger
                deb = pdb.Pdb(stdin=sys.__stdin__, stdout=sys.__stdout__)
                deb.reset()
                deb.interaction(None, sys.exc_info()[2])
            return TaskError("PythonAction Error", exception)
        finally:
            # restore std streams /log captured streams
            if capture_io:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                self.out = output.getvalue()
                self.err = errput.getvalue()
            else:
                if out:
                    sys.stdout = old_stdout
                if err:
                    sys.stderr = old_stderr

    def _handle_return(self, value, called):
        # if callable returns false. Task failed
        match value:
            case False:
                return TaskFailed("Python Task failed: '%s' returned %s" % (called, value))
            case True | None:
                return None
            case str():
                self.result = value
            case dict():
                self.values = value
                self.result = value
            case BaseAction():
                return value
            case TaskFailed() | TaskError():
                return value
            case _:
                return TaskError("Python Task error: '%s'. It must return:\n"
                                "False for failed task.\n"
                                "True, None, string or dict for successful task\n"
                                "returned %s (%s)" %
                                (called, value, type(value)))

    def _capture_io(self, out, err) -> tuple:
        # set std stream
        output     = StringIO()
        out_writer = Writer()
        # capture output but preserve isatty() from original stream
        out_writer.add_writer(output)
        if out:
            out_writer.add_writer(out, is_original=True)
        sys.stdout = out_writer

        errput     = StringIO()
        err_writer = Writer()
        err_writer.add_writer(errput)
        if err:
            err_writer.add_writer(err, is_original=True)
        sys.stderr = err_writer

        return output, errput

class DootTaskExt(Task):
    """
    Extension of doit.Task to allow returning an Action from an action,
    making a task's `execute` a stack of actions instead of a list
    """
    action_builder = DootPyActionExt.build
    name_splitter = re.compile(r":+|\.")

    def __init__(self, *args, **kwargs):
        pass
        super().__init__(*args, **{x:y for x,y in kwargs.items() if x in Task.valid_attr or x == 'loader'})
        if self.meta is None:
            self.meta = dict()
        self.meta.update({x:y for x,y in kwargs.items() if x not in Task.valid_attr})

    @property
    def actions(self):
        """lazy creation of action instances"""
        if self._action_instances is None:
            builder = DootTaskExt.action_builder
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
