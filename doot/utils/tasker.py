#!/usr/bin/env python3
"""
Utility classes for building tasks with a bit of structure
"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref
from doit.task import Task as DoitTask
from doot.errors import DootDirAbsent

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging


class DootTasker:
    """ Util Class for building single tasks  """

    def __init__(self, base:str, dirs:DirData=None):
        self.create_doit_tasks = self._build_task
        self.base              = base
        self.dirs              = dirs

    def params(self) -> list:
        return []

    def default_task(self) -> dict:
        return dict([("basename" , self.base),
                     ("meta"     , self.default_meta()),
                     ("actions"  , list()),
                     ("task_dep" , [ self.dirs.checker ] if self.dirs is not None else []),
                     ("doc"      , self.doc),
                     ("uptodate" , [self.is_current]),
                     ("clean"    , [self.clean]),
                     ("params"   , self.params() ),
                     ])

    def default_meta(self) -> dict:
        meta = dict()
        return meta

    @property
    def doc(self):
        try:
            split_doc = [x for x in self.__class__.__doc__.split("\n") if bool(x)]
            return ":: " + split_doc[0].strip() if bool(split_doc) else ""
        except AttributeError:
            return ":: default"

    def is_current(self, task:DoitTask):
        return False

    def clean(self, task:DoitTask):
        return

    def task_detail(self, task:dict) -> dict:
        return task

    def _build_task(self):
        task = self.default_task()
        try:
            return self.task_detail(task)
        except DootDirAbsent:
            return None


class DootSubtasker(DootTasker):
    """ Util class for building subtasks,
    Provides points for a setup, teardown, top task
    and subtasks
    """

    def __init__(self, base:str, dirs:DirData=None):
        self.create_doit_tasks = self._build_tasks
        self.base = base
        self.dirs = dirs

    def default_task(self):
        task = super().default_task()
        task['name'] = None
        return task
    def subtask_actions(self, fpath) -> list[str|CmdAction|Callable]:
        return [f"echo {fpath}"]

    def subtask_detail(self, fpath:pl.Path, task:dict) -> None|dict:
        """
        override to add any additional task details
        """
        return task

    def setup_detail(self, task:dict) -> None|dict:
        task['uptodate'] = [False]
        return task
    def teardown_detail(self, task:dict) -> None|dict:
        task['uptodate'] = [False]
        return task

    def top_detail(self, task:dict) -> None|dict:
        task['uptodate'] = [False]
        return task

    def _build_setup(self) -> dict:
        """
        Build a pre-task that every subtask depends on
        """
        try:
            task_spec = self.default_task()
            task_spec['basename'] = f"_{self.base}"
            task_spec['name'] = "pre"
            val = self.setup_detail(task_spec)
            return val
        except DootDirAbsent:
            return None

    def _build_subtask(self, n:int, uname, fpath):
        try:
            spec_doc  = self.doc + f" : {fpath}"
            task_spec = self.default_task()
            task_spec.update({"name"     : uname,
                              "doc"      : spec_doc,
                              "task_dep" : [f"_{self.base}:pre"]
                              })
            task_spec['meta'].update({ "n" : n })
            task = self.subtask_detail(fpath, task_spec)
            task['actions'] += self.subtask_actions(fpath)
            return task
        except DootDirAbsent:
            return None

    def _build_teardown(self, subnames:list[str]) -> dict:
        try:
            task_spec = self.default_task()
            task_spec.update({
                "basename" : f"_{self.base}",
                "name"     : "post",
                "task_dep" : subnames,
                "doc"      : "Post Action",
            })
            task = self.teardown_detail(task_spec)
            return task
        except DootDirAbsent:
            return None

    def _build_tasks(self):
        raise NotImplementedError()
