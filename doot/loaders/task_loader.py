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
from doot.constants import DEFAULT_TASK_GROUP
from doot._abstract.loader import TaskLoader_i

TASK_STRING : Final[str] = "task_"
prefix_len  : Final[int] = len(TASK_STRING)


task_path       = doot.config.on_fail(".tasks").task_path(wrapper=pl.Path)
allow_overloads = doot.config.on_fail(False, bool).allow_overloads()

def apply_group_and_source(group, source, x):
    x['group']  = x.get('group', group)
    x['source'] = str(source)
    return x

class DootTaskLoader(TaskLoader_i):
    """
    load toml defined tasks
    """
    taskers       : dict[str, tuple(dict, Tasker_i)] = {}
    cmd_names     : set[str]                         = set()
    task_builders : dict[str,Any]                    = dict()
    extra : Tomler

    def setup(self, plugins, extra=None) -> Self:
        logging.debug("---- Registering Task Builders")
        self.cmd_names     = set(map(lambda x: x.name, plugins.get("command", [])))
        self.taskers       = {}
        self.task_builders = {}
        for plugin in tomler.Tomler(plugins).on_fail([]).tasker():
            if plugin.name in self.task_builders:
                logging.warning("Conflicting Task Builder Type Name: %s: %s / %s",
                                plugin.name,
                                self.task_builders[plugin.name],
                                plugin)
                continue

            try:
                self.task_builders[plugin.name] = plugin.load()
            except ModuleNotFoundError as err:
                logging.warning(f"Bad Task Builder Plugin Specified: %s", plugin)
        else:
            logging.debug("Registered Task Builders: %s", self.task_builders.keys())


        match extra: # { group : [task_dicts] }
            case None:
                self.extra = {}
            case list():
                self.extra = {"_": extra}
            case dict() | tomler.Tomler():
                self.extra = tomler.Tomler(extra).on_fail({}).tasks()
        logging.debug("Task Loader Setup with %s extra tasks", len(self.extra))
        return self


    def load(self) -> Tomler[tuple[dict, type]]:
        start_time = time.perf_counter()
        logging.debug("---- Loading Tasks")
        raw_specs = []
        for source in doot._configs_loaded_from:
            task_specs = tomler.load(source).on_fail({}).tasks()
            raw_specs += self._load_raw_specs(task_specs, source)

        if self.extra:
            raw_specs += self._load_raw_specs(self.extra, "(extra)")
        raw_specs += self._load_spec_path(task_path)
        logging.debug("Loaded %s Task Specs", len(raw_specs))
        if bool(self.taskers):
            logging.warning("Task Loader is overwriting already loaded tasks")
        self.taskers = self._build_task_classes(raw_specs, self.cmd_names)

        logging.debug("Task List Size: %s", len(self.taskers))
        logging.debug("Task List Names: %s", list(self.taskers.keys()))
        logging.debug("---- Tasks Loaded in %s seconds", f"{time.perf_counter() - start_time:0.4f}")
        return tomler.Tomler(self.taskers)

    def _load_raw_specs(self, data, source) -> list[dict]:
        raw_specs = []
        # Load from doot.toml task specs
        for group, data in data.items():
            if not isinstance(data, list):
                logging.warning("Unexpected task specification format: %s : %s", group, data)
            else:
                raw_specs += map(ftz.partial(apply_group_and_source, group, source), data)

        logging.info("Loaded Tasks from: %s", source)
        return raw_specs

    def _load_spec_path(self, path):
        raw_specs = []
        # Load task spec path
        if not path.exists():
            pass
        elif path.is_dir():

            for task_file, data in [(x, tomler.load(x)) for x in path.iterdir() if x.suffix == ".toml"]:
                for group, val in data.on_fail({}).tasks().items():
                    # sets 'group' for each task if it hasn't been set already
                    raw_specs += map(ftz.partial(apply_group_and_source, group, task_file), val)
                logging.info("Loaded Tasks from: %s", task_file)
        elif path.is_file():
            for group, val in tomler.load(path).on_fail({}).tasks().items():
                # sets 'group' for each task if it hasn't been set already
                raw_specs += map(ftz.partial(apply_group_and_source, group, path), val)
            logging.info("Loaded Tasks from: %s", path)

        return raw_specs


    def _build_task_classes(self, group_specs:list, command_names) -> dict[str, tuple[dict, type]]:
        """
        get task creators defined in the config
        """
        task_descriptions : dict[str, tuple[dict, type]] = {}
        for spec in group_specs:
            match spec:
                ##-- failures
                case {"name": task_name} if task_name in command_names:
                    raise ResourceWarning(f"Task / Cmd name conflict: {task_name}")
                case {"name": task_name, "group": group} if (task_name in task_descriptions
                                                             and group == task_descriptions[task_name][0]['group']
                                                             and not allow_overloads):
                    raise ResourceWarning(f"Task Name Overloaded: ", task_name, group)
                case {"name": task_name, "type": task_type} if task_type not in self.task_builders:
                    raise ResourceWarning(f"Task Spec '{task_name}' Load Failure: Bad Type Name: '{task_type}'. Source file: {spec['source']}. Available: {self.task_builders.keys()}")
                ##-- end failures
                case {"name": task_name, "class": task_class}:
                    if task_name in task_descriptions:
                        logging.warning("Overloading Task: %s : %s", task_name, task_class)

                    try:
                        mod_name, class_name = task_class.split("::")
                        mod = importlib.import_module(mod_name)
                        cls = getattr(mod, class_name)
                        task_descriptions[task_name] = (spec, cls)
                    except ModuleNotFoundError as err:
                        raise ResourceWarning(f"Task Spec '{task_name}' Load Failure: Bad Module Name: '{task_class}'. Source File: {spec['source']}") from err
                    except AttributeError as err:
                        raise ResourceWarning(f"Task Spec '{task_name}' Load Failure: Bad Class Name: '{task_class}'. Source File: {spec['source']}") from err
                    except ValueError as err:
                        raise ResourceWarning(f"Task Spec '{task_name}' Load Failure: Module/Class Split failed on: '{task_class}'. Source File: {spec['source']}") from err
                case {"name": task_name, "type": task_type}:
                    cls = self.task_builders[task_type]
                    task_descriptions[task_name] = (spec, cls)
                case _:
                    raise ResourceWarning(f"Task Spec missing, at least, a name and class or type: {spec['source']}: {spec}")

        return task_descriptions
