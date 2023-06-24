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
from doot._abstract.tasker import Tasker_i
from doot._abstract.loader import TaskLoader_i
from doot.control.locations import DootLocData
from doot.task.task import DootTask
from doot.utils.check_dirs import CheckDir
from doot.utils.gen_toml import GenToml
from doot.utils.task_namer import task_namer

TASK_STRING : Final[str] = "task_"
prefix_len  : Final[int] = len(TASK_STRING)

task_specs = doot.config.on_fail({}).tasks()
task_path  = doot.config.on_fail(".tasks").task_path(wrapper=pl.Path)
allow_overloads = doot.config.on_fail(False, bool).allow_overloads()

def apply_group(group, x):
    x['group'] = x.get('group', group)
    return x

class DootTaskLoader(TaskLoader_i):
    """
    load toml defined tasks
    """

    def setup(self, plugins, extra=None):
        self.taskers : dict[str, tuple(dict, Tasker_i)] = {}
        self.cmd_names     = set(map(lambda x: x.name, plugins.get("command", [])))
        self.task_builders = {}
        for plugin in tomler.Tomler(plugins).on_fail([]).task():
            if plugin.name in self.task_builders:
                logging.warning("Conflicting Task Builder Type Name: %s: %s / %s",
                                plugin.name,
                                self.task_builders[plugin.name],
                                plugin)
                continue

            try:
                self.task_builders[plugin.name] = plugin.load()
            except ModuleNotFoundError as err:
                logging.warning(f"Bad Task Builder Plugin Specified Plugin: %s", plugin)
        else:
            logging.info("Registered Task Builders: %s", self.task_builders.keys())


        match extra: # { group : [task_dicts] }
            case None:
                self.extra = {}
            case list():
                self.extra = {"_": extra}
            case dict() | tomler.Tomler():
                self.extra = tomler.Tomler(extra).on_fail({}).tasks()
        logging.debug("Task Loader Setup with %s extra tasks", len(self.extra))


    def load(self) -> Tomler:
        start_time = time.perf_counter()
        logging.debug("---- Loading Tasks")
        raw_specs = []
        raw_specs += self._load_raw_specs(task_specs)
        if self.extra:
            raw_specs += self._load_raw_specs(self.extra)
        raw_specs += self._load_spec_path(task_path)
        logging.debug("Loaded %s Task Specs", len(raw_specs))
        self._build_task_classes(raw_specs, self.cmd_names)

        logging.debug("Task List Size: %s", len(self.taskers))
        logging.debug("Task List Names: %s", list(self.taskers.keys()))
        logging.debug("---- Tasks Loaded in %s seconds", f"{time.perf_counter() - start_time:0.4f}")
        return tomler.Tomler(self.taskers)

    def _load_raw_specs(self, data):
        raw_specs = []
        # Load from doot.toml task specs
        for group, data in data.items():
            if not isinstance(data, list):
                logging.warning("Unexpected task specification format: %s : %s", group, data)
            else:
                raw_specs += map(ftz.partial(apply_group, group), data)

        return raw_specs

    def _load_spec_path(self, path):
        raw_specs = []
        # Load task spec path
        if not path.exists():
            pass
        elif path.is_dir():
            logging.info("Loading Task Path: %s", path)
            for key, val in tomler.load_dir(path).on_fail({}).tasks().items():
                # sets 'group' for each task if it hasn't been set already
                raw_specs += map(lambda x: (x.__setitem__('group', x.get('group', key)), x)[1], val)
        elif path.is_file():
            for key, val in tomler.load(path).on_fail({}).tasks().items():
                # sets 'group' for each task if it hasn't been set already
                raw_specs += map(lambda x: (x.__setitem__('group', x.get('group', key)), x)[1], val)

        return raw_specs


    def _build_task_classes(self, group_specs:list, command_names):
        """
        get task creators defined in the config
        """
        for spec in group_specs:
            match spec:
                case {"name": task_name} if task_name in command_names:
                    raise ResourceWarning(f"Task / Cmd name conflict: {task_name}")
                case {"name": task_name} if task_name in self.taskers and not allow_overloads:
                    raise ResourceWarning(f"Task Name Overloaded: {task_name}")
                case {"name": task_name, "class": task_class}:
                    if task_name in self.taskers:
                        logging.warning("Overloading Task: %s : %s", task_name, task_class)

                    try:
                        mod_name, class_name = task_class.split("::")
                        mod = importlib.import_module(mod_name)
                        cls = getattr(mod, class_name)
                        self.taskers[task_name] = (spec, cls)
                    except ModuleNotFoundError as err:
                        raise ResourceWarning(f"Task Spec {task_name} Load Failure: Bad Module Name: {task_class}") from err
                    except AttributeError as err:
                        raise ResourceWarning(f"Task Spec {task_name} Load Failure: Bad Class Name: {task_class}") from err
                case {"name": task_name, "type": task_type} if task_type not in self.task_builders:
                    raise ResourceWarning(f"Task Spec {task_name} Load Failure: Bad Type Name: {task_type}. Available: {self.task_builders.keys()}")
                case {"name": task_name, "type": task_type}:
                    cls = self.task_builders[task_type]
                    self.taskers[task_name] = (spec, cls)
                case _:
                    raise ResourceWarning("Task Spec needs, at least, a name and class or type: %s", spec)
