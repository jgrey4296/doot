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

from doot.mixins.filer import FilerMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
import doot
from doot import tasker, globber

class MoveLogs(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, FilerMixin):
    """
    Move logs in the direct root directory, to a logs directory
    """

    def __init__(self, name="logs::move", locs=None, roots=None):
        super().__init__(name, locs, roots=roots or [locs.root], rec=False)
        self.output      = locs.logs
        self.history_reg = re.compile(r"^..+?_history")

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir():
            return self.globc.accept
        return self.globc.discard

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.move_logs, [fpath]),
                          (self.move_histories, [fpath]),
                         ],
        })
        return task

    def move_logs(self, fpath):
        logs = filter(lambda x: x.stem == "log", fpath.iterdir())
        self.move_to(self.output, *logs, fn="overwrite")

    def move_histories(self, fpath):
        histories = filter(lambda x: self.history_reg.match(x.name), fpath.iterdir())
        self.move_to(self.output, *histories, fn="overwrite")
