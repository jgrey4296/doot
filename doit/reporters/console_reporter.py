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

class ConsoleReporter:
    """Default reporter. print results on console/terminal (stdout/stderr)

    @ivar failure_verbosity: (int) include captured stdout/stderr on failure
                             report even if already shown.
    """
    # short description, used by the help system
    desc = 'console output'

    def __init__(self, outstream, options):
        # save non-successful result information (include task errors)
        self.failures = []
        self.runtime_errors = []
        self.failure_verbosity = options.get('failure_verbosity', 0)
        self.outstream = outstream

    def write(self, text):
        self.outstream.write(text)

    def initialize(self, tasks, selected_tasks):
        """called just after tasks have been loaded before execution starts"""
        pass


    def get_status(self, task):
        """called when task is selected (check if up-to-date)"""
        pass

    def execute_task(self, task):
        """called when execution starts"""
        # ignore tasks that do not define actions
        # ignore private/hidden tasks (tasks that start with an underscore)
        if task.actions and (task.name[0] != '_'):
            self.write('.  %s\n' % task.title())

    def add_failure(self, task, fail: BaseFail):
        """called when execution finishes with a failure"""
        result = {'task': task, 'exception': fail}
        if fail.report:
            self.failures.append(result)
            self._write_failure(result)

    def add_success(self, task):
        """called when execution finishes successfully"""
        pass

    def skip_uptodate(self, task):
        """skipped up-to-date task"""
        if task.name[0] != '_':
            self.write("-- %s\n" % task.title())

    def skip_ignore(self, task):
        """skipped ignored task"""
        self.write("!! %s\n" % task.title())

    def cleanup_error(self, exception):
        """error during cleanup"""
        sys.stderr.write(exception.get_msg())

    def runtime_error(self, msg):
        """error from doit (not from a task execution)"""
        # saved so they are displayed after task failures messages
        self.runtime_errors.append(msg)

    def teardown_task(self, task):
        """called when starts the execution of teardown action"""
        pass


    def _write_failure(self, result, write_exception=True):
        msg = '%s - taskid:%s\n' % (result['exception'].get_name(),
                                    result['task'].name)
        self.write(msg)
        if write_exception:
            self.write(result['exception'].get_msg())
            self.write("\n")

    def complete_run(self):
        """called when finished running all tasks"""
        # if test fails print output from failed task
        for result in self.failures:
            task = result['task']
            # makes no sense to print output if task was not executed
            if not task.executed:
                continue
            show_err = task.verbosity < 1 or self.failure_verbosity > 0
            show_out = task.verbosity < 2 or self.failure_verbosity == 2
            if show_err or show_out:
                self.write("#" * 40 + "\n")
            if show_err:
                self._write_failure(result,
                                    write_exception=self.failure_verbosity)
                err = "".join([a.err for a in task.actions if a.err])
                self.write("{} <stderr>:\n{}\n".format(task.name, err))
            if show_out:
                out = "".join([a.out for a in task.actions if a.out])
                self.write("{} <stdout>:\n{}\n".format(task.name, out))

        if self.runtime_errors:
            self.write("#" * 40 + "\n")
            self.write("Execution aborted.\n")
            self.write("\n".join(self.runtime_errors))
            self.write("\n")
