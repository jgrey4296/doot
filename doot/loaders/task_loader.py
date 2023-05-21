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

from collections import ChainMap
import importlib
import tomler
import doot
from doot.constants import default_task_group
from doot._abstract.tasker import DootTasker_i
from doot._abstract.loader import TaskLoader_i
from doot.control.locations import DootLocData
from doot.task.task import DootTask
from doot.utils.check_dirs import CheckDir
from doot.utils.gen_toml import GenToml
from doot.utils.task_namer import task_namer

TASK_STRING = "task_"

task_specs = doot.config.on_fail([]).tasks()
task_path  = doot.config.on_fail(".tasks").task_path(wrapper=pl.Path)
allow_overloads = doot.config.on_fail(False, bool).allow_overloads()

class DootTaskLoader(TaskLoader_i):
    """
    """

    def setup(self, plugins):
        self.cmd_names = set(map(lambda x: x._name, plugins.get("command", [])))
        self.task_creators : dict[str, tuple(dict, DootTasker_i)] = {}

    def load(self, arg:Tomler) -> dict:
        start_time = time.perf_counter()
        logging.debug("---- Loading Tasks")
        specs : list = self._get_task_specs(arg)
        self._get_task_creators(specs, self.cmd_names)

        logging.debug("Task List Size: %s", len(self.task_creators))
        logging.debug("Task List Names: %s", list(self.task_creators.keys()))
        logging.debug("---- Tasks Loaded in %s seconds", f"{time.perf_counter() - start_time:0.4f}")
        return self.task_creators

    def _get_task_specs(self, extra) -> list:
        specs     = None
        raw_specs = []
        match task_specs:
            case list():
                raw_specs += map(lambda x: (x.__setattr('group', x.get('group', default_task_group)), x)[1], task_specs)
            case dict() | tomler.Tomler():
                for key, val in task_specs.items():
                    # sets 'group' for each task if it hasn't been set already
                    raw_specs += map(lambda x: (x.__setitem__('group', x.get('group', key)), x)[1], val)

        match extra:
            case None:
                pass
            case dict() | tomler.Tomler():
                for key, val in extra.get('tasks', {}).items():
                    # sets 'group' for each task if it hasn't been set already
                    raw_specs += map(lambda x: (x.__setitem__('group', x.get('group', key)), x)[1], val)

        if not task_path.exists():
            pass
        elif task_path.is_dir():
            logging.info("Loading Task Path: %s", task_path)
            for key, val in tomler.load_dir(task_path).on_fail({}).tasks().items():
                # sets 'group' for each task if it hasn't been set already
                raw_specs += map(lambda x: (x.__setitem__('group', x.get('group', key)), x)[1], val)
        elif task_path.is_file():
            for key, val in tomler.load(task_path).on_fail({}).tasks().items():
                # sets 'group' for each task if it hasn't been set already
                raw_specs += map(lambda x: (x.__setitem__('group', x.get('group', key)), x)[1], val)

        return raw_specs


    def _get_task_creators(self, group_specs:list, command_names):
        """
        get task creators defined in the config

        A task-creator is a function that:
        - is a DootTasker
        """
        logging.debug("Getting Task Creators from namespace")
        prefix_len : int                = len(TASK_STRING)

        for spec in group_specs:
            match spec:
                case {"name": task_name} if task_name in command_names:
                    raise ResourceWarning(f"Task / Cmd name conflict: {task_name}")
                case {"name": task_name} if task_name in self.task_creators and not allow_overloads:
                    raise ResourceWarning(f"Task Name Overloaded: {task_name}")
                case {"name": task_name, "class": task_class}:
                    if task_name in self.task_creators:
                        logging.warning("Overloading Task: %s : %s", task_name, task_class)

                    try:
                        mod_name, class_name = task_class.split("::")
                        mod = importlib.import_module(mod_name)
                        cls = getattr(mod, class_name)
                        self.task_creators[task_name] = (spec, cls)
                    except ModuleNotFoundError as err:
                        raise ResourceWarning(f"Task Spec {task_name} Load Failure: Bad Module Name: {task_class}") from err
                    except AttributeError as err:
                        raise ResourceWarning(f"Task Spec {task_name} Load Failure: Bad Class Name: {task_class}") from err
                case _:
                    raise ResourceWarning("Task Spec needs, at least, a name and class: %s", spec)
