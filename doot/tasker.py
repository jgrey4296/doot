#!/usr/bin/env python3
"""
Utility classes for building tasks with a bit of structure
"""
##-- imports
from __future__ import annotations

import abc
import itertools
import logging as logmod
import pathlib as pl
import sys
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from time import sleep
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import datetime
import fileinput
import shutil
import zipfile
from random import randint
from types import FunctionType, MethodType

from doit.action import CmdAction
from doit.task import Task as DoitTask
from doit.task import dict_to_task
from doit.tools import Interactive

from doot.errors import DootDirAbsent
from doot.utils.general import ForceCmd


class DootTasker:
    """ Util Class for building single tasks

    """
    sleep_subtask : ClassVar[Final[float]]
    sleep_notify  : ClassVar[Final[bool]]

    @staticmethod
    def set_defaults(config:Tomler):
        DootTasker.sleep_subtask = config.on_fail(2.0,   int|float).tool.doot.subtask.sleep()
        DootTasker.sleep_notify  = config.on_fail(False, bool).tool.doot.notify.sleep()

    def __init__(self, base:str, locs:DootLocData=None, output=None):
        assert(base is not None)
        assert(locs is not None or locs is False), locs

        # Wrap in a lambda because MethodType does not behave as we need it to
        self.create_doit_tasks = lambda *a, **kw: self._build(*a, **kw)
        self.create_doit_tasks.__dict__['basename'] = base

        self.base         = base
        self.locs         = locs
        self.args         = {}
        self._setup_name  = None
        self.active_setup = False
        self.output       = output

        params = self.set_params()
        if bool(params):
            self.create_doit_tasks.__dict__['_task_creator_params'] = params

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

    def setup_detail(self, task:dict) -> None|dict:
        return task

    def task_detail(self, task:dict) -> dict:
        return task

    def log(self, msg, level=logmod.DEBUG):
        logging.log(level, msg)

    @property
    def setup_name(self):
        if self._setup_name is not None:
            return self._setup_name

        private = "_" if self.base[0] != "_" else ""
        full = f"{private}{self.base}:setup"
        return full

    def _build_setup(self) -> DoitTask:
        """
        Build a pre-task that every subtask depends on
        """
        try:
            task_spec             = self.default_task()
            task_spec['name']     = self.setup_name
            if self.locs is not None and not isinstance(self.locs, bool):
                task_spec['setup'] = [ self.locs.checker ]

            match self.setup_detail(task_spec):
                case None:
                    return None
                case str() as sname:
                    self._setup_name = sname
                    return None
                case dict() as val:
                    self.active_setup = True
                    return dict_to_task(val)
                case _ as val:
                    logging.warning("Setup Detail Returned an unexpected value: ", val)
        except DootDirAbsent:
            return None

    def _build_task(self):
        logging.debug("Building Task for: %s", self.base)
        task                     = self.default_task()
        maybe_task : None | dict = self.task_detail(task)
        if maybe_task is None:
            return None
        if self.active_setup:
            maybe_task['setup'] += [self.setup_name]

        full_task = dict_to_task(maybe_task)
        return full_task

    def _build(self, **kwargs):
        try:
            self.args.update(kwargs)
            setup_task = self._build_setup()
            task       = self._build_task()

            if task is not None:
                yield task
            else:
                return None
            if setup_task is not None:
                yield setup_task

        except Exception as err:
            logging.error("ERROR: Task Creation Failure: ", err, file=sys.stderr)
            logging.error("ERROR: Task was: ", self.base, file=sys.stderr)
            sys.exit(1)

class DootSubtasker(DootTasker):
    """ Extends DootTasker to make subtasks

    add a name in task_detail to run actions after all subtasks are finished
    """

    def __init__(self, base:str, locs, **kwargs):
        super().__init__(base, locs, **kwargs)

    def subtask_detail(self, task, **kwargs) -> None|dict:
        return task

    def _build_task(self):
        task = super()._build_task()
        task.has_subtask = True
        task.update_deps({'task_dep': [f"{self.base}:*"] })
        if self.active_setup:
            task.update_deps({"task_dep": [self.setup_name]})
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

            if self.active_setup:
                task['setup'] += [self.setup_name]

            if bool(self.sleep_subtask):
                task['actions'].append(self._sleep_subtask)

            return task
        except DootDirAbsent:
            return None

    def _build_subs(self):
        raise NotImplementedError()

    def _build(self, **kwargs):
        try:
            self.args.update(kwargs)
            setup_task = self._build_setup()
            task       = self._build_task()
            subtasks   = self._build_subs()

            if task is None:
                return None
            yield task

            if setup_task is not None:
                yield setup_task

            for x in subtasks:
                yield x

        except Exception as err:
            logging.error("ERROR: Task Creation Failure: ", err, file=sys.stderr)
            logging.error("ERROR: Task was: ", self.base, file=sys.stderr)
            sys.exit(1)

    def _sleep_subtask(self):
        if self.sleep_notify:
            logging.info("Sleep Subtask")
        sleep(self.sleep_subtask)

