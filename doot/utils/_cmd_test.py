#!/usr/bin/env python3
"""
Cmd experiment based on doit-graph
"""
##-- imports

##-- end imports

##-- default imports
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

##-- end default imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doit.cmd_base import DoitCmdBase
from doit.control import TaskControl


class JGTestCmd(DoitCmdBase):
    """
    a test doot command
    """
    name            = 'graph'
    doc_purpose     = "create task's dependency-graph (in dot file format)"
    doc_description = ""
    doc_usage       = "[TASK ...]"
    cmd_options     = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _execute(self, pos_args=None):
        # init
        control       = TaskControl(self.task_list)
        self.tasks    = control.tasks

        print("Tasks:")
        for x in self.tasks.values():
            print(x.name)
        # task = control.tasks.get(...)

        print("Test Command")
