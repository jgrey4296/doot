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
                    cast, final, overload, runtime_checkable, Generator)
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

from tomler import Tomler
import doot
from doot.enums import TaskFlags
from doot.structs import DootTaskSpec, TaskStub, TaskStubPart
from doot._abstract import Tasker_i, Task_i
from doot.errors import DootDirAbsent

@doot.check_protocol
class DootTasker(Tasker_i):
    """ Util Class for building single tasks
      wraps with setup and teardown tasks,
      manages cleaning,
      and holds state

    """
    _help = ["A Basic Task Constructor"]
    _default_flags = TaskFlags.TASKER

    def __init__(self, spec:DootTaskSpec):
        super(DootTasker, self).__init__(spec)
        assert(spec is not None), "Spec is empty"

    def _build_task(self) -> None|Task_i|DootTaskSpec:
        logging.debug("Building Task for: %s", self.name)
        task                             = self.default_task()
        maybe_task : None | DootTaskSpec = self.specialize_task(task)

        match maybe_task:
            case None:
                return None
            case _ if not bool(maybe_task.doc):
                maybe_task.doc = self.doc
                return maybe_task
            case _:
                return maybe_task

    def default_task(self) -> DootTaskSpec:
        return DootTaskSpec(name=self.name)

    def is_stale(self, task:Task_i):
        return False

    def build(self, **kwargs) -> Generator[Task_i|dict]:
        logging.debug("-- tasker %s expanding tasks", self.name)
        if bool(kwargs):
            logging.debug("recieved kwargs: %s", kwargs)
        self.args.update(kwargs)
        task       = self._build_task()

        if task is not None:
            yield task
        else:
            return None

    def specialize_task(self, task):
        return task

    @classmethod
    def stub_class(cls):
        stub = TaskStub(ctor=cls.__class__)
        stub['doc'].default   = [f"\"{x}\"" for x  in cls.class_help().split("\n")]
        stub['flags'].default = cls._default_flags
        return stub

    def stub_instance(self):
        stub                      = self.__class__.stub_class()
        stub['name'].default      = self.fullname
        if bool(self.doc):
            stub['doc'].default   = [f"\"{x}\"" for x in self.doc]
        stub['flags'].default     = self.spec.flags
        return stub
