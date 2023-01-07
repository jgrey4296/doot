#!/usr/bin/env python3
"""
Utility classes for building tasks with a bit of structure
"""
##-- imports
from __future__ import annotations

from time import sleep
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

import doot
from doot.errors import DootDirAbsent
from doot.utils.gen_toml import GenToml

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

subtask_sleep : int = doot.config.or_get(2).tool.doot.subtask_sleep()
batch_sleep   : int = doot.config.or_get(2).tool.doot.batch_sleep()
max_batches   : int = doot.config.or_get(-1).tool.doot.max_batches()

class DootTasker:
    """ Util Class for building single tasks  """

    def __init__(self, base:str, dirs:DirData=None):
        self.create_doit_tasks = self._build_task
        self.base              = base
        self.dirs              = dirs
        self.setup_name        = "setup"

        if hasattr(self, 'gen_toml') and callable(self.gen_toml):
            GenToml.add_generator(self.base, self.gen_toml)

    def params(self) -> list:
        return []

    def default_task(self) -> dict:
        return dict([("basename" , self.base),
                     ("meta"     , self.default_meta()),
                     ("actions"  , list()),
                     ("task_dep" , list()),
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
            return ":: "

    def is_current(self, task:DoitTask):
        return False

    def clean(self, task:DoitTask):
        return

    @property
    def setup_names(self):
        names = { "base" : f"_{self.base}",
                  "name" : f"{self.setup_name}"
                 }
        names['full'] = f"{names['base']}:{names['name']}"
        return names

    def setup_detail(self, task:dict) -> None|dict:
        return task

    def task_detail(self, task:dict) -> dict:
        return task

    def _build_setup(self) -> dict:
        """
        Build a pre-task that every subtask depends on
        """
        try:
            snames = self.setup_names
            task_spec = self.default_task()
            task_spec['basename'] = snames['base']
            task_spec['name'] = snames['name']
            if self.dirs is not None:
                task_spec['setup'] = [ self.dirs.checker ]

            val = self.setup_detail(task_spec)
            return val
        except DootDirAbsent:
            return None

    def _build_task(self):
        try:
            task          = self.default_task()
            task['setup'] = [self.setup_names['full']]
            maybe_task : None | dict = self.task_detail(task)
            if maybe_task is None:
                return None
            yield maybe_task
            yield self._build_setup()
        except DootDirAbsent:
            yield None


class DootSubtasker(DootTasker):
    """ Util class for building subtasks in groups,

    add a name in task_detail to run actions after all subtasks are finished
    """

    def __init__(self, base:str, dirs:DirData=None):
        super().__init__(base, dirs)
        self.batch_count = 0

    def reset_batch_count(self):
        self.batch_count = 0

    def subtask_detail(self, fpath, task) -> None|dict:
        return task

    def subtask_actions(self, fpath) -> list[str|CmdAction|Callable]:
        return [f"echo {fpath}"]

    def _build_subtask(self, n:int, uname, fpath):
        try:
            spec_doc  = self.doc + f" : {fpath}"
            task_spec = self.default_task()
            task_spec.update({"name"     : uname,
                              "doc"      : spec_doc,
                              "setup"    : [self.setup_names['full']]
                              })
            task_spec['meta'].update({ "n" : n })
            task = self.subtask_detail(fpath, task_spec)
            task['actions'] += self.subtask_actions(fpath)
            if bool(subtask_sleep):
                task['actions'].append(self._sleep_subtask)
            return task
        except DootDirAbsent:
            return None

    def _build_task(self):
        raise NotImplementedError()


    def run_batch(self, *batch_data) -> bool:
        """
        handles batch bookkeeping
        """
        for data in batch_data:
            self.batch(data)

        self.batch_count += 1
        if -1 < max_batches < batch_count:
            return True
        print("Sleep Batch")
        sleep(batch_sleep)
        return False

    def _sleep_subtask(self):
        print("Sleep Subtask")
        sleep(subtask_sleep)

    def batch(self, data):
        """ Override to implement what a batch does """
        pass
