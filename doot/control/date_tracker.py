#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

# import abc
# import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator, Literal)
# from uuid import UUID, uuid1
# from weakref import ref

# from bs4 import BeautifulSoup
import boltons.queueutils
import networkx as nx
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from collections import defaultdict
import doot
import doot.errors
import doot.constants as const
from doot.enums import TaskStateEnum
from doot._abstract import Job_i, Task_i, FailPolicy_p
from doot.structs import DootTaskArtifact, DootTaskSpec, DootTaskName
from doot._abstract import TaskTracker_i, TaskRunner_i, TaskBase_i
from doot.task.base_task import DootTask
from doot.control.tracker import _TrackerEdgeType, DootTracker

STORAGE_FILE : Final[pl.Path] = doot.config.on_fail(DootKey.make(".tasks.bk")).settings.general.tracker_file(wrapper=DootKey.make).to_path()

@doot.check_protocol
class DootDateTracker(DootTracker):
    """
      Track task status, using file product modification times
      reads and writes modification times to wherever config.settings.general.tracker_file locates

    """
    def __init__(self, shadowing:bool=False, *, policy=None):
        super().__init__(shadowing=shadowing, policy=policy)
        self._modification_db = None

    def write(self, target:pl.Path) -> None:
        """ Write the dependency graph to a file """
        # STORAGE_FILE.write_text(str(self._modification_db))
        raise NotImplementedError()

    def read(self, target:pl.Path) -> None:
        """ Read the dependency graph from a file """
        # self._modification_db = STORAGE_FILE.read_text()
        raise NotImplementedError()

    def update_state(self, task:str|TaskBase_i|DootTaskArtifact|DootTaskName, state:self.state_e):
        now = datetime.datetime.now()
        match state:
            case self.state_e.EXISTS:
                task_date  = self._modification_db.set(str(task), now)
                self._invalidate_descendents(task)
                pass
            case self.state_e.FAILED:
                self._invalidate_descendents(task)
                pass
            case self.state_e.SUCCESS:
                pass

    def _invalidate_descendents(task):
        incomplete, descendants = self._task_dependents(task)
        pass
