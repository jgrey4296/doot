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

class PythonAction(BaseAction):
    """Python action. Execute a python callable.

    @ivar py_callable: (callable) Python callable
    @ivar args: (sequence)  Extra arguments to be passed to py_callable
    @ivar kwargs: (dict) Extra keyword arguments to be passed to py_callable
    @ivar task(Task): reference to task that contains this action
    @ivar pm_pdb: if True drop into PDB on exception when executing task
    """
    pm_pdb = False

    def __init__(self, py_callable, args=None, kwargs=None, task=None):
        # pylint: disable=W0231
        self.py_callable = py_callable
        self.task = task
        self.out = None
        self.err = None
        self.result = None
        self.values = {}

        if args is None:
            self.args = []
        else:
            self.args = args

        if kwargs is None:
            self.kwargs = {}
        else:
            self.kwargs = kwargs

        # check valid parameters
        if not hasattr(self.py_callable, '__call__'):
            msg = "%r PythonAction must be a 'callable' got %r."
            raise InvalidTask(msg % (self.task, self.py_callable))
        if inspect.isclass(self.py_callable):
            msg = "%r PythonAction can not be a class got %r."
            raise InvalidTask(msg % (self.task, self.py_callable))
        if inspect.isbuiltin(self.py_callable):
            msg = "%r PythonAction can not be a built-in got %r."
            raise InvalidTask(msg % (self.task, self.py_callable))
        if type(self.args) is not tuple and type(self.args) is not list:
            msg = "%r args must be a 'tuple' or a 'list'. got '%s'."
            raise InvalidTask(msg % (self.task, self.args))
        if type(self.kwargs) is not dict:
            msg = "%r kwargs must be a 'dict'. got '%s'"
            raise InvalidTask(msg % (self.task, self.kwargs))


    def _prepare_kwargs(self):
        return BaseAction._prepare_kwargs(self.task, self.py_callable,
                                          self.args, self.kwargs)

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

        if capture_io:
            # set std stream
            old_stdout = sys.stdout
            output = StringIO()
            out_writer = Writer()
            # capture output but preserve isatty() from original stream
            out_writer.add_writer(output)
            if out:
                out_writer.add_writer(out, is_original=True)
            sys.stdout = out_writer

            old_stderr = sys.stderr
            errput = StringIO()
            err_writer = Writer()
            err_writer.add_writer(errput)
            if err:
                err_writer.add_writer(err, is_original=True)
            sys.stderr = err_writer
        else:
            if out:
                old_stdout = sys.stdout
                sys.stdout = out
            if err:
                old_stderr = sys.stderr
                sys.stderr = err


        kwargs = self._prepare_kwargs()

        # execute action / callable
        try:
            returned_value = self.py_callable(*self.args, **kwargs)
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

        # if callable returns false. Task failed
        if returned_value is False:
            return TaskFailed("Python Task failed: '%s' returned %s" %
                              (self.py_callable, returned_value))
        elif returned_value is True or returned_value is None:
            pass
        elif isinstance(returned_value, str):
            self.result = returned_value
        elif isinstance(returned_value, dict):
            self.values = returned_value
            self.result = returned_value
        elif isinstance(returned_value, (TaskFailed, TaskError)):
            return returned_value
        else:
            return TaskError("Python Task error: '%s'. It must return:\n"
                             "False for failed task.\n"
                             "True, None, string or dict for successful task\n"
                             "returned %s (%s)" %
                             (self.py_callable, returned_value,
                              type(returned_value)))

    def __str__(self):
        # get object description excluding runtime memory address
        return "Python: %s" % str(self.py_callable)[1:].split(' at ')[0]

    def __repr__(self):
        return "<PythonAction: '%s'>" % (repr(self.py_callable))
