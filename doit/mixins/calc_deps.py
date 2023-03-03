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

from doot.utils.task_namer import task_namer

class CalcDepsMixin:

    @property
    def calc_dep_taskname(self):
        return task_namer(self.basename, "calc_deps", private=True)

    def calc_action(self):
        """
        The action which is overriden to calculate dependencies
        """
        return { "file_dep": [], "task_dep": [], "calc_dep": [] }

    def _build_task(self):
        task = super()._build_task()
        if task is None:
            return task

        task.calc_dep.add(self.calc_dep_taskname)
        return task

    def _build_calc_task(self):
        return {
            "basename" : self.calc_dep_taskname,
            "actions"  : [ self.calc_action ],
        }

    def build(self, **kwargs):
        yield from super().build(**kwargs)
        yield self._build_calc_task()
