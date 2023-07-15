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


class Reporter_i:

    def __init__(self, outstream, options):
        # save non-successful result information (include task errors)
        self.failures          = []
        self.runtime_errors    = []
        self.failure_verbosity = options.get('failure_verbosity', 0)
        self.outstream         = outstream

    def __str__(self):
        raise NotImplementedError()



    def initialize(self, tasks, selected_tasks):
        """called just after tasks have been loaded before execution starts"""
        raise NotImplementedError()

    def get_status(self, task):
        """called when task is selected (check if up-to-date)"""
        raise NotImplementedError()

    def execute_task(self, task):
        """called when execution starts"""
        # ignore tasks that do not define actions
        # ignore private/hidden tasks (tasks that start with an underscore)
        raise NotImplementedError()

    def add_failure(self, task, fail: BaseFail):
        """called when execution finishes with a failure"""
        raise NotImplementedError()

    def add_success(self, task):
        """called when execution finishes successfully"""
        raise NotImplementedError()

    def skip_uptodate(self, task):
        """skipped up-to-date task"""
        raise NotImplementedError()

    def skip_ignore(self, task):
        """skipped ignored task"""
        raise NotImplementedError()

    def cleanup_error(self, exception):
        """error during cleanup"""
        raise NotImplementedError()

    def runtime_error(self, msg):
        """error from doot (not from a task execution)"""
        # saved so they are displayed after task failures messages
        raise NotImplementedError()

    def teardown_task(self, task):
        """called when starts the execution of teardown action"""
        raise NotImplementedError()

    def complete_run(self):
        """called when finished running all tasks"""
        # if test fails print output from failed task
        raise NotImplementedError()
