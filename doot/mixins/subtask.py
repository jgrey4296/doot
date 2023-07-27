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
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot import namer
from doot.errors import DootDirAbsent
from time import sleep

class SubMixin:

    def subtask_detail(self, task, **kwargs) -> None|dict:
        return task

    def _sleep_subtask(self):
        if self.sleep_notify:
            logging.info("Sleep Subtask")
        sleep(self.sleep_subtask)

    @property
    def subtask_regex(self):
        return namer(self.fullname, "*", private=True)

    @property
    def subtask_base(self):
        return namer(self.fullname, private=True)

    def subtask_name(self, val):
        return namer(self.fullname, val, private=True)

    def _build_task(self) -> None|DoitTask:
        task = super()._build_task()
        if task is None:
            return None

        updates =  { "task_dep" : [self.subtask_regex] }
        task.update_deps(updates)
        task.has_subtask = True
        return task

    def _build_subs(self):
        raise NotImplementedError()

    def _build_subtask(self, n:int, uname, **kwargs) -> dict:
        try:
            spec_doc  = self.doc + f" : {kwargs}"
            task_spec = self.default_task()
            task_spec.update({
                "basename" : self.subtask_base,
                "name"     : str(uname),
                "doc"      : spec_doc,
            })
            task_spec['meta'].update({ "n" : n })

            task = self.subtask_detail(task_spec, **kwargs)
            if task is None:
                return

            if not task_spec.get("private", True):
                task_spec['basename'] = task_spec['basename'][1:]

            if self.has_active_setup:
                task['setup'] += [self.setup_name]

            if bool(self.sleep_subtask):
                task['actions'].append(self._sleep_subtask)

            task['actions'] = [x for x in task['actions'] if bool(x)]
            return task
        except DootDirAbsent:
            return None

    def build(self, **kwargs) -> Generator:
        yield from super().build(**kwargs)
        yield from self._build_subs()
