#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

# import abc
# import datetime
import enum
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
import networkx as nx
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


printer = logmod.getLogger("doot._printer")

from collections import defaultdict
import doot
from doot.enums import TaskStateEnum
from doot._abstract import Tasker_i, Task_i
from doot._abstract import TaskTracker_i, TaskRunner_i, TaskOrdering_p


class DootRunner(TaskRunner_i):

    def __init__(self, tracker, reporter):
        self.tracker       = tracker
        self.reporter      = reporter
        self.teardown_list = []  # list of tasks to be teardown
        self.final_result  = "SUCCESS"  # until something fails
        self._stop_running = False

    def __call__(self, *tasks:str):
        """ tasks are initial targets to run.
          so loop on the tracker, getting the next task,
          running its actions,
          and repeating,
          until done

          if task is a tasker, it is expanded and added into the tracker
          """
        for task in iter(self.tracker):
            # Do Task
            self._execute_task(task)
            # Update it's status
            self.tracker.update_task_state(task, TaskStateEnum.SUCCESS)



        raise NotImplementedError()

    def _execute_task(self, task:Tasker_i|Task_i):
        """execute task's actions"""



    def _process_task_result(self, node, base_fail):
        """handles result"""
        raise NotImplementedError()

    def _execute_action(self, action):
        """   """
        raise NotImplementedError()

    def _teardown(self):
        """run teardown from all tasks"""
        raise NotImplementedError()

    def _finish(self):
        """finish running tasks"""
        raise NotImplementedError()
