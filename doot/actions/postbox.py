## base_action.py -*- mode: python -*-
##-- imports
from __future__ import annotations

# import abc
import datetime
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

##-- end imports

from collections import defaultdict
from time import sleep
import sh
import doot
from doot.errors import DootTaskError, DootTaskFailed
from doot._abstract import Action_p

printer = logmod.getLogger("doot._printer")
"""
  Postbox: Each Task Tree gets one, as a set[Any]
  Each Task can put something in its own postbox.
  And can read any other task tree's postbox, but not modify it.

"""

class DootPostBox:

    boxes : ClassVar[dict[str,set[Any]]]] = defaultdict(set)

    @staticmethod
    def put(key, val):
        DootPostBox.boxes[key].add(val)

    @staticmethod
    def get(key):
        return DootPostBox.boxes[key]

@doot.check_protocol
class PutPostAction(Action_p):
    """
      push data to the inter-task postbox of this task tree
      The arguments of the action are held in self.spec
    __call__ is passed a *copy* of the task's state dictionary

    """

    def __str__(self):
        return f"Postbox Put Action: {self.spec.args}"

    def expand_str(self, val, state):
        return val.format_map(state)

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        DootPostBox.put(task_state['_task_name'].root(), task_state.get(spec.args[0]))

@doot.check_protocol
class GetPostAction(Action_p):
    """
      Read data from the inter-task postbox of a task tree
      The arguments of the action are held in self.spec
    __call__ is passed a *copy* of the task's state dictionary

    """

    def __str__(self):
        return f"Postbox Get Action: {self.spec.args}"

    def expand_str(self, val, state):
        return val.format_map(state)

    def __call__(self, spec, task_state_copy:dict) -> dict|bool|None:
        return {spec.kwargs.target : DootPostBox.get(spec.kwargs.source) }

@doot.check_protocol
class SummarizePostAction(Action_p):
    """
      print a summary of this task tree's postbox
      The arguments of the action are held in self.spec
    __call__ is passed a *copy* of the task's state dictionary

    """

    def __str__(self):
        return f"Postbox Summary Action: {self.spec.args}"

    def expand_str(self, val, state):
        return val.format_map(state)

    def __call__(self, spec, task_state_copy:dict) -> dict|bool|None:
        data = DootPostBox.get(spec.kwargs.source)
        printer.info("Postbox %s Contents: %s", spec.kwargs.source, data)
