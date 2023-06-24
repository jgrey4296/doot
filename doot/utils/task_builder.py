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
##-- end logging

from doot._abstract.tasker import Tasker_i

class DootTaskBuilder:

    def __init__(self):
        self._task_collection = {}

    def build_tasks(self, taskers:dict[str, tuple(dict, Tasker_i)], args=()):
        """
        Run each task creator, or delay it
        """
        for name, ref in taskers:
            # Parse command line arguments for task generator parameters
            delayed        = getattr(ref, "_build_delayed", None) or getattr(ref, 'doit_create_after', None)

            match delayed:
                case True:
                    delay_obj = DelayedLoader(None)
                    self._build_delayed(name, ref, delay_obj)
                    continue
                case FunctionType() | MethodType():
                    delay_name = getattr(ref, "delayed_subtask_name", task_namer(ref.basename, "delayed", private=True))
                    self._build_delayed(delay_name, delayed, DelayedLoader(None))
                case DelayedLoader() if bool(delayed.creates):
                    for tname in delayed.creates:
                        self._build_delayed(tname, ref, delayed)
                case DelayedLoader():
                    self._build_delayed(name, ref, delayed)
                case None:
                    pass

            self._generate_tasks(name, ref)

    def _build_delayed(self, tname, delay_fn, original_delayed):
        # Here we re-assign with the reference taken on doit load phase
        # because it is bounded method.
        logging.debug("Delaying: %s", tname)
        this_delayed = copy(original_delayed)
        this_delayed.creator = delay_fn
        d_task = self._task_class(tname, None, loader=this_delayed, doc=original_delayed.creator.__doc__)
        self._add_task(d_task)

    def _add_task(self, task):
        if task is None:
            return

        if task.subtask_of is not None:
            match self._task_collection.get(task.subtask_of, None):
                case None:
                    logging.warning("No Group Task found for Sub Task: %s", task.name)
                    self._build_failures.append(task)
                    return
                case group_task:
                    group_task.task_dep.append(task.name)

        if self._task_collection.get(task.name, False):
            logging.warning("Duplicate Task Name Specified: %s", task.name)
            self._build_failures.append(task)
            return

        self._task_collection[task.name] = task

    def _generate_tasks(self, func_name, gen_result, gen_doc=None) -> list:
        new_task = None
        match gen_result:
            case doit_loader.Task():
                # a task instance, just return it without any processing
                logging.debug("Task is a Task Object, nothing to do: %s", gen_result.name)
                new_task = gen_result
            case Tasker_i():
                self._generate_tasks(func_name, gen_result.build(), gen_doc)
            case FunctionType() | MethodType():
                self._generate_tasks(func_name, gen_result(), gen_doc)
            case {"head_task" : _ }:
                new_task = self._generate_solo_task(func_name, gen_result, gen_doc)
            case { "basename": base, "name" : _ }:
                if gen_result['basename'] not in self._task_collection:
                    leader_task = self._generate_solo_task(base, {"actions": [], "head_task": True}, gen_doc)
                    self._add_task(leader_task)
                new_task = self._generate_sub_task(func_name, gen_result, gen_doc)
            case dict():
                new_task = self._generate_solo_task(func_name, gen_result, gen_doc)
            case GeneratorType():
                logging.debug("%s : Task is a generator, running", func_name)
                for sub_result in gen_result:
                    self._generate_tasks(func_name, sub_result, gen_doc=gen_doc)
                logging.debug("%s : Generator Finished", func_name)
            case [*maybe_tasks]:
                for sub_task in maybe_tasks:
                    self._generate_tasks(func_name, sub_task, gen_doc=gen_doc)
            case None:
                pass
            case _:
                logging.warning("Unrecognized Task creator result: %s", gen_result)
                self._build_failures.append(gen_result)

        self._add_task(new_task)

    def _generate_solo_task(self, func_name, task_dict, gen_doc):
        """generate a single task from a dict returned by a task generator"""
        logging.debug("Generator %s Returned a Value, building task from it", func_name)
        private = task_dict.get("private", False)
        task_dict['name'] = task_namer(task_dict.pop('basename', func_name), private=private)
        # Use task generator docstring
        # if no doc present in task dict
        if 'doc' not in task_dict:
            task_dict['doc'] = gen_doc

        task = self._task_class(**task_dict)
        if task_dict.get("head_task", False):
            task.has_subtask = True

        return task

    def _generate_sub_task(self, func_name, task_dict, gen_doc):
        """generate a single task from a dict yielded by task generator

        @param tasks: dictionary with created tasks
        @return None: the created task is added to 'tasks' dict
        """
        logging.debug("Generator %s yielded value, building task from it", func_name)
        basename          = task_dict.pop('basename', None) or func_name
        private           = task_dict.get("private", True)
        task_dict['name'] = task_namer(basename, task_dict.get('name', ""), private=private)
        if 'doc' not in task_dict:
            task_dict['doc'] = gen_doc

        sub_task            = self._task_class(**task_dict)
        sub_task.subtask_of = task_namer(basename)
        return sub_task
