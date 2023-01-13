#!/usr/bin/env python3
"""
Utility classes for building tasks with a bit of structure
"""
##-- imports
from __future__ import annotations

from time import sleep
import abc
import logging as logmod
import itertools
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

from doit import task_params
from doit.task import dict_to_task


class DootTasker:
    """ Util Class for building single tasks
    registers 'gen_toml' methods for automatically

    'run_batch' controls batching bookkeeping,
    'batch' is the actual action
    """
    subtask_sleep : ClassVar[float]
    batch_sleep   : ClassVar[float]
    max_batches   : ClassVar[int]

    @staticmethod
    def set_defaults(config:TomlAccess):
        DootTasker.subtask_sleep = config.or_get(2.0).tool.doot.subtask_sleep()
        DootTasker.batch_sleep   = config.or_get(2.0).tool.doot.batch_sleep()
        DootTasker.max_batches   = config.or_get(-1).tool.doot.max_batches()

    def __init__(self, base:str, dirs:DirData=None):
        assert(base is not None)
        assert(dirs is not None or dirs is False), dirs

        self.create_doit_tasks = lambda *a, **kw: self._build_task(*a, **kw)
        self.create_doit_tasks.__dict__['basename'] = base
        params = self.set_params()
        if bool(params):
            self.create_doit_tasks.__dict__['_task_creator_params'] = params

        self.base              = base
        self.dirs              = dirs
        self.setup_name        = "setup"
        self.batch_count       = 0
        self.params            = {}

        if hasattr(self, 'gen_toml') and callable(self.gen_toml):
            from doot.utils.gen_toml import GenToml
            GenToml.add_generator(self.base, self.gen_toml)

    def set_params(self) -> list:
        return []

    def default_task(self) -> dict:
        return dict([("name"     , self.base),
                     ("meta"     , self.default_meta()),
                     ("actions"  , list()),
                     ("task_dep" , list()),
                     ("setup"    , list()),
                     ("doc"      , self.doc),
                     ("uptodate" , [self.is_current]),
                     ("clean"    , [self.clean]),
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
    def _setup_names(self):
        private = "_" if self.base[0] != "_" else ""
        names = { "base" : f"{private}{self.base}",
                  "name" : f"{self.setup_name}",
                  "full" : f"{private}{self.base}:{self.setup_name}"
                 }
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
            snames                = self._setup_names
            task_spec             = self.default_task()
            task_spec['name']     = snames['full']
            if self.dirs is not None and self.dirs is not False:
                task_spec['setup'] = [ self.dirs.checker ]

            val = self.setup_detail(task_spec)
            if val is not None:
                return dict_to_task(val)
        except DootDirAbsent:
            return None

    def _build_task(self, **kwargs):
        try:
            self.params.update(kwargs)
            task                     = self.default_task()
            maybe_task : None | dict = self.task_detail(task)
            if maybe_task is None:
                return None
            setup_task = self._build_setup()
            if setup_task is not None:
                yield setup_task
                maybe_task['setup'].append(self._setup_names['full'])

            full_task = dict_to_task(maybe_task)
            yield full_task
        except DootDirAbsent:
            return None



    def _sleep_subtask(self):
        print("Sleep Subtask")
        sleep(self.subtask_sleep)

    def _reset_batch_count(self):
        self.batch_count = 0

    def run_batch(self, *batches, reset=True, **kwargs):
        """
        handles batch bookkeeping
        """
        if reset:
            self._reset_batch_count()

        for data in batches:
            batch_list = [x for x in data if x is not None]
            if not bool(batch_list):
                continue
            print(f"Batch: {self.batch_count} : ({len(batch_list)})")
            self.batch(batch_list, **kwargs)

            self.batch_count += 1
            if -1 < self.max_batches < self.batch_count:
                print("Max Batch Hit")
                return
            print("Sleep Batch")
            sleep(self.batch_sleep)

    def batch(self, data, **kwargs):
        """ Override to implement what a batch does """
        pass



    def chunk(self, iterable, n, *, incomplete='fill', fillvalue=None):
        """Collect data into non-overlapping fixed-length chunks or blocks
        from https://docs.python.org/3/library/itertools.html
         grouper('ABCDEFG', 3, fillvalue='x') --> ABC DEF Gxx
         grouper('ABCDEFG', 3, incomplete='strict') --> ABC DEF ValueError
         grouper('ABCDEFG', 3, incomplete='ignore') --> ABC DEF
        """
        args = [iter(iterable)] * n
        if incomplete == 'fill':
            return itertools.zip_longest(*args, fillvalue=fillvalue)
        if incomplete == 'strict':
            return zip(*args, strict=True)
        if incomplete == 'ignore':
            return zip(*args)
        else:
            raise ValueError('Expected fill, strict, or ignore')

        
class DootSubtasker(DootTasker):
    """ Extends DootTasker to make subtasks

    add a name in task_detail to run actions after all subtasks are finished
    """

    def __init__(self, base:str, dirs:DirData=None):
        super().__init__(base, dirs)


    def subtask_detail(self, task, **kwargs) -> None|dict:
        return task

    def _build_subtask(self, n:int, uname, **kwargs):
        try:
            spec_doc  = self.doc + f" : {kwargs}"
            task_spec = self.default_task()
            task_spec.update({"name"     : f"{uname}",
                              "doc"      : spec_doc,
                              })
            task_spec['meta'].update({ "n" : n })
            task = self.subtask_detail(task_spec, **kwargs)
            if task is None:
                return

            if bool(self.subtask_sleep):
                task['actions'].append(self._sleep_subtask)

            return task
        except DootDirAbsent:
            return None

    def _build_task(self, **kwargs):
        raise NotImplementedError()


