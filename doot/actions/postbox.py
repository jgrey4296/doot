## base_action.py -*- mode: python -*-
"""
  Postbox: Each Task Tree gets one, as a set[Any]
  Each Task can put something in its own postbox.
  And can read any other task tree's postbox, but not modify it.

"""
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
import doot.utils.expansion as exp

printer = logmod.getLogger("doot._printer")

##-- expansion keys
FROM_KEY    : Final[exp.DootKey] = exp.DootKey("from")
UPDATE      : Final[exp.DootKey] = exp.DootKey("update_")
TASK_NAME   : Final[exp.DootKey] = exp.DootKey("_task_name")
##-- end expansion keys

class _DootPostBox:
    """
      Internal Postbox class.
      holds a static variable of `boxes`, which maps task roots -> unique postbox
      Postboxes are lists, values are appended to it
    """

    boxes : ClassVar[dict[str,list[Any]]] = defaultdict(list)

    @staticmethod
    def put(key, val):
        _DootPostBox.boxes[key].append(val)

    @staticmethod
    def put_from(state, val):
        """
        utility to add to a postbox using the state, instead of calculating the root yourself
        """
        _DootPostBox.boxes[state['_task_name'].root()].append(val)

    @staticmethod
    def get(key) -> list:
        return _DootPostBox.boxes[key]


@doot.check_protocol
class PutPostAction(Action_p):
    """
      push data to the inter-task postbox of this task tree
      The arguments of the action are held in self.spec
    """

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        for arg in spec.args:
            data = exp.to_any(arg, spec, task_state)
            match data:
                case None:
                    pass
                case []:
                    pass
                case _:
                    _DootPostBox.put(task_state['_task_name'].root(), data)

@doot.check_protocol
class GetPostAction(Action_p):
    """
      Read data from the inter-task postbox of a task tree
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = [FROM_KEY, UPDATE]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        from_task = FROM_KEY.to_type(spec, task_state, type_=str|None) or task_state[TASK_NAME].root()
        data_key  = UPDATE.redirect(spec)
        return { data_key : _DootPostBox.get(from_task) }

@doot.check_protocol
class SummarizePostAction(Action_p):
    """
      print a summary of this task tree's postbox
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = [FROM_KEY, "full"]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        from_task = FROM_KEY.to_type(spec, task_state, type_=str|None) or task_state[TASK_NAME].root()
        data   = _DootPostBox.get(from_task)
        if spec.kwargs.on_fail(False, bool).full():
            for x in data:
                printer.info("Postbox %s: Item: %s", from_task, str(x))

        printer.info("Postbox %s: Size: %s", from_task, len(data))
