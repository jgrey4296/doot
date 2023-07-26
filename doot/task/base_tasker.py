#!/usr/bin/env python3
"""
Utility classes for building tasks with a bit of structure
"""
##-- imports
from __future__ import annotations

# import abc
# import datetime
# import enum
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
                    cast, final, overload, runtime_checkable)
# from uuid import UUID, uuid1
# from weakref import ref

# from bs4 import BeautifulSoup
# import boltons
# import construct as C
# import dirty-equals as deq
# import graphviz
# import matplotlib.pyplot as plt
# import more_itertools as itzplus
# import networkx as nx
# import numpy as np
# import pandas
# import pomegranate as pom
# import pony import orm
# import pronouncing
# import pyparsing as pp
# import rich
# import seaborn as sns
# import sklearn
# import stackprinter # stackprinter.set_excepthook(style='darkbg2')
# import sty
# import sympy
# import tomllib
# import toolz
# import tqdm
# import validators
# import z3
# import spacy # nlp = spacy.load("en_core_web_sm")

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


import doot
from doot._abstract.tasker import Tasker_i
from doot._abstract.task import Task_i
from doot.errors import DootDirAbsent

class DootTasker(Tasker_i):
    """ Util Class for building single tasks
      wraps with setup and teardown tasks,
      manages cleaning,
      and holds state

    """
    sleep_subtask : ClassVar[Final[float]]
    sleep_notify  : ClassVar[Final[bool]]
    _help = ["A Basic Task Constructor"]

    @staticmethod
    def set_defaults(config:Tomler):
        DootTasker.sleep_subtask = config.on_fail(2.0,   int|float).subtask.sleep()
        DootTasker.sleep_notify  = config.on_fail(False, bool).notify.sleep()

    def __init__(self, spec:dict|Tomler):
        super(DootTasker, self).__init__(spec)

        assert(spec is not None), "Spec is empty"

        self.spec             = spec
        self.args             = {}
        self._setup_name      = None
        self.has_active_setup = False

        # match base:
        #     case str():
        #         self.basename         = base
        #         self.subgroups        = subgroups or []
        #     case [x, *xs]:
        #         self.basename = x
        #         self.subgroups = xs + (subgroups or [])
        #     case _:
        #         raise TypeError("Bad base name provided to task: %s", base)


    def _build_setup(self) -> None|DootTask:
        """
        Build a pre-task that every subtask depends on
        """
        try:
            task_spec         = self.default_task()
            task_spec['doc']  = ""
            task_spec['name'] = self.setup_name
            # if self.locs is not None and not isinstance(self.locs, bool):
            #     task_spec['setup'] = [ self.locs.checker ]

            match self.setup_detail(task_spec):
                case None:
                    return None
                case str() as sname:
                    self._setup_name = sname
                    return None
                case dict() as val:
                    self.has_active_setup = True
                    val['actions'] = [x for x in val['actions'] if bool(x)]
                    return self._make_task(**val)
                case _ as val:
                    logging.warning("Setup Detail Returned an unexpected value: ", val)
        except DootDirAbsent:
            return None

    def _build_task(self) -> None|DootTask:
        logging.debug("Building Task for: %s", self.fullname)
        task                     = self.default_task()
        maybe_task : None | dict = self.task_detail(task)
        if maybe_task is None:
            return None
        if self.has_active_setup:
            maybe_task['setup'] += [self.setup_name]

        maybe_task['actions'] = [x for x in maybe_task['actions'] if bool(x)]
        full_task             = self._make_task(**maybe_task)
        if not bool(full_task.doc):
            full_task.doc = self.doc
        return full_task

    @property
    def priors(self) -> list:
        pass

    @property
    def posts(self) -> list:
        pass

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

    def is_current(self, task:DootTask):
        return False

    def clean(self, task:DootTask):
        return

    def build(self, **kwargs) -> Generator[DootTask|dict]:
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
