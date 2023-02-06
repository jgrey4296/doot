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

import doot
from doot import tasker, globber, task_mixins

class MoveLogs(globber.LazyGlobMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin):

    def __init__(self, name="logs::move", locs=None, roots=None):
        super().__init__(name, locs, roots=roots or [locs.root], rec=False)
        self.output      = locs.logs
        self.history_reg = re.compile(r"^..+?_history")

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.move_logs, [fpath]),
                          (self.move_histories, [fpath]),
                         ],
        })
        return task

    def move_logs(self, fpath):
        logs = [ x for x in fpath.iterdir() if x.stem == "log" ]
        self.move_to(self.output, *logs, fn="overwrite")

    def move_histories(self, fpath):
        histories = [x for x in fpath.iterdir() if self.history_reg.match(x.name)]
        self.move_to(self.output, *histories, fn="overwrite")
