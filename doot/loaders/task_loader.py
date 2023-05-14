#!/usr/bin/env python3
"""

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
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

import tomler
import doot
from doot._abstract.tasker import DootTasker_i
from doot.control.group import TaskGroup
from doot.control.locations import DootLocData
from doot.task.task import DootTask
from doot.utils.check_dirs import CheckDir
from doot.utils.gen_toml import GenToml
from doot.utils.task_namer import task_namer

TASK_STRING = "task_"

class DootTaskLoader(TaskLoader_i):
    """
    Task loader that automatically
    retrieves directory checks, and stores all created tasks
    for later retrieval
    """

    def setup(self, plugins):
        self.cmd_names = set(plugins.get("command", [])) # get from plugins
        self.task_creators : dict[str, DootTasker_i] = {}
        self._build_failures  = []
        self._task_class      = DootTaskExt
        try:
            self.__doot_all_dirs   = DootLocData.as_taskgroup()
            self.__doot_all_checks = CheckDir.as_taskgroup()
        except doot.errors.DootDirAbsent as err:
            logging.error("LOCATION MISSING: %s", err.args[0])
            sys.exit(1)

    def load_tasks(self) -> dict:
        start_time = time.perf_counter()
        logging.debug("---- Loading Tasks")
        self._get_task_creators(self.namespace, self.cmd_names)

        logging.debug("Task List Size: %s", len(self.task_creators))
        logging.debug("Task List Names: %s", list(self.task_creators.keys()))
        if bool(self._build_failures):
            logging.warning("%s task build failures", len(self._build_failures))
        logging.debug("---- Tasks Loaded in %s seconds", f"{time.perf_counter() - start_time:0.4f}")
        return self.task_creators

    def _get_task_creators(self, namespace, command_names):
        """
        get task creators defined in the namespace

        A task-creator is a function that:
        - task_name starts with the string TASK_STRING
        - is a DootTasker

        @return (list - func) task-creators
        """
        logging.debug("Getting Task Creators from namespace")
        prefix_len : int                = len(TASK_STRING)

        for task_name, ref in namespace.items():
            match task_name.startswith(TASK_STRING), ref:
                case _, _ if task_name in command_names:
                    logging.warning("doot_loader.Task can't be called '%s' because this is a command task_name.", task_name)
                    continue
                case _, _ if task_name in self.task_creators:
                    logging.warning("Overloaded Task Name", task_name)
                    continue
                case _, TaskGroup() if bool(ref):
                    logging.debug("Expanding TaskGroup: %s", ref)
                    self.task_creators.update([(getattr(x, "basename", task_name), x) for x in ref.tasks])
                case _,  DootTasker_i():
                    self.task_creators.update([(ref.basename, ref)])
                case True, dict():
                    logging.info("Got a basic task dict: %s", task_name)
                    self.task_craetors[task_name] = DictTasker(ref)
                case True, FunctionType() | MethodType():
                    # function is a task creator because of its task_name
                    # remove TASK_STRING prefix from task_name
                    self.task_creators[task_name[prefix_len:]] = FunctionTasker(ref)
                case _, _:
                    continue

        return creators
