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

from types import LambdaType
import datetime
import fileinput
import shutil
import zipfile
from random import randint
from types import FunctionType, MethodType

from doot.errors import DootDirAbsent
from doot.actions.force_cmd_action import ForceCmd
from doot.task.task_ext import DootTaskExt
from doot.utils.task_namer import task_namer

class DootTasker:
    """ Util Class for building single tasks

    """
    sleep_subtask : ClassVar[Final[float]]
    sleep_notify  : ClassVar[Final[bool]]

    @staticmethod
    def set_defaults(config:Tomler):
        DootTasker.sleep_subtask = config.on_fail(2.0,   int|float).subtask.sleep()
        DootTasker.sleep_notify  = config.on_fail(False, bool).notify.sleep()

    def __init__(self, base:str|list, locs:DootLocData=None, output=None, subgroups=None):
        assert(base is not None)
        assert(locs is not None or locs is False), locs

        # Wrap in a lambda because MethodType does not behave as we need it to
        match base:
            case str():
                self.basename         = base
                self.subgroups        = subgroups or []
            case [x, *xs]:
                self.basename = x
                self.subgroups = xs + (subgroups or [])
            case _:
                raise TypeError("Bad base name provided to task: %s", base)

        self.locs             = locs
        self.args             = {}
        self._setup_name      = None
        self.has_active_setup = False
        self.output           = output

    @property
    def setup_name(self):
        if self._setup_name is not None:
            return self._setup_name

        self._setup_name = task_namer(self.basename, "setup", private=True)
        return self._setup_name

    @property
    def fullname(self):
        return task_namer(self.basename, *self.subgroups)

    @property
    def doc(self):
        try:
            split_doc = [x for x in self.__class__.__doc__.split("\n") if bool(x)]
            return ":: " + split_doc[0].strip() if bool(split_doc) else ""
        except AttributeError:
            return ":: "

    def set_params(self) -> list:
        return []

    def default_task(self) -> dict:
        return dict([("name"     , self.fullname),
                     ("meta"     , self.default_meta()),
                     ("actions"  , list()),
                     ("task_dep" , list()),
                     ("setup"    , list()),
                     ("doc"      , self.doc),
                     ("uptodate" , [self.is_current]),
                     ("clean"    , [self.clean]),
                     ("targets"  , []),
                     ])

    def default_meta(self) -> dict:
        meta = dict()
        return meta

    def is_current(self, task:DoitTask):
        return False

    def clean(self, task:DoitTask):
        return

    def setup_detail(self, task:dict) -> None|dict:
        return task

    def task_detail(self, task:dict) -> dict:
        return task

    def log(self, msg, level=logmod.DEBUG, prefix=None):
        prefix = prefix or ""
        lines  = []
        match msg:
            case str():
                lines.append(msg)
            case LambdaType():
                lines.append(msg())
            case [LambdaType()]:
                lines += msg[0]()
            case list():
                lines += msg

        for line in lines:
            logging.log(level, prefix + str(line))

    def _build_setup(self) -> None|DoitTask:
        """
        Build a pre-task that every subtask depends on
        """
        try:
            task_spec         = self.default_task()
            task_spec['doc']  = ""
            task_spec['name'] = self.setup_name
            if self.locs is not None and not isinstance(self.locs, bool):
                task_spec['setup'] = [ self.locs.checker ]

            match self.setup_detail(task_spec):
                case None:
                    return None
                case str() as sname:
                    self._setup_name = sname
                    return None
                case dict() as val:
                    self.has_active_setup = True
                    val['actions'] = [x for x in val['actions'] if bool(x)]
                    return DootTaskExt(**val)
                case _ as val:
                    logging.warning("Setup Detail Returned an unexpected value: ", val)
        except DootDirAbsent:
            return None

    def _build_task(self) -> None|DoitTask:
        logging.debug("Building Task for: %s", self.fullname)
        task                     = self.default_task()
        maybe_task : None | dict = self.task_detail(task)
        if maybe_task is None:
            return None
        if self.has_active_setup:
            maybe_task['setup'] += [self.setup_name]

        maybe_task['actions'] = [x for x in maybe_task['actions'] if bool(x)]
        full_task             = DootTaskExt(**maybe_task)
        if not bool(full_task.doc):
            full_task.doc = self.doc
        return full_task

    def build(self, **kwargs) -> Generator[DoitTask|dict]:
        logging.debug("Building Tasker: %s", self.fullname)
        if bool(kwargs):
            logging.debug("Recieved kwargs: %s", kwargs)
        self.args.update(kwargs)
        setup_task = self._build_setup()
        task       = self._build_task()

        if task is not None:
            yield task
        else:
            return None

        if setup_task is not None:
            yield setup_task
