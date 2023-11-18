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
from doot.utils.string_expand import expand_str, expand_key, expand_to_obj

printer = logmod.getLogger("doot._printer")
"""
  Postbox: Each Task Tree gets one, as a set[Any]
  Each Task can put something in its own postbox.
  And can read any other task tree's postbox, but not modify it.

"""

class DootPostBox:

    boxes : ClassVar[dict[str,set[Any]]] = defaultdict(set)

    @staticmethod
    def put(key, val):
        DootPostBox.boxes[key].add(val)

    @staticmethod
    def put_from(state, val):
        """
        utility to add to a postbox using the state, instead of calculating the root yourself
        """
        DootPostBox.boxes[state['_task_name'].root()].add(val)

    @staticmethod
    def get(key):
        return DootPostBox.boxes[key]


@doot.check_protocol
class PutPostAction(Action_p):
    """
      push data to the inter-task postbox of this task tree
      The arguments of the action are held in self.spec
    """

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        for arg in spec.args:
            data = expand_to_obj(arg, spec, task_state)
            DootPostBox.put(task_state['_task_name'].root(), data)

@doot.check_protocol
class GetPostAction(Action_p):
    """
      Read data from the inter-task postbox of a task tree
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = ["from_task", "update_"]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        if "from_task" in spec.kwargs or "from_task_" in spec.kwargs:
            from_task = expand_key(spec.kwargs.on_fail("from_task").from_task_(), spec, task_state)
        else:
            from_task = task_state['_task_name'].root()

        data_key  = expand_str(spec.kwargs.update_, spec, task_state)
        return { data_key : DootPostBox.get(from_task) }

@doot.check_protocol
class SummarizePostAction(Action_p):
    """
      print a summary of this task tree's postbox
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = ["from_"]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        from_task = expand_key(spec.kwargs.on_fail(task_state['_task_name'].root()).from_task(),
                               spec, task_state)

        data   = DootPostBox.get(from_task)
        printer.info("Postbox %s: Contents: %s", target, data)
