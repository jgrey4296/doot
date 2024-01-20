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
from doot.structs import DootKey

printer = logmod.getLogger("doot._printer")

##-- expansion keys
FROM_KEY    : Final[DootKey] = DootKey.make("from")
UPDATE      : Final[DootKey] = DootKey.make("update_")
TASK_NAME   : Final[DootKey] = DootKey.make("_task_name")
SUBKEY      : Final[DootKey] = DootKey.make("subkey")
##-- end expansion keys

class _DootPostBox:
    """
      Internal Postbox class.
      holds a static variable of `boxes`, which maps task roots -> unique postbox
      Postboxes are lists, values are appended to it
    """

    boxes : ClassVar[dict[str,list[Any]]] = defaultdict(lambda: defaultdict(list))
    default_subkey                        = "_default"

    @staticmethod
    def put(key, val, subkey=None):
        subkey = subkey or _DootPostBox.default_subkey
        match val:
            case None | [] | {} | dict() if not bool(val):
                pass
            case list() | set():
                _DootPostBox.boxes[key][subkey] += val
            case _:
                _DootPostBox.boxes[key][subkey].append(val)

    @staticmethod
    def put_from(state, val, subkey=None):
        """
        utility to add to a postbox using the state, instead of calculating the root yourself
        """
        key    = TASK_NAME.to_type(None, state).root()
        subkey = subkey or _DootPostBox.default_subkey
        _DootPostBox.put(key, val, subkey=subkey)

    @staticmethod
    def get(key, subkey=Any) -> list:
        match subkey:
            case x if x == Any:
                return _DootPostBox.boxes[key][_DootPostBox.default_subkey][:]
            case None:
                return _DootPostBox.boxes[key].copy()
            case _:
                return _DootPostBox.boxes[key][subkey]

    @staticmethod
    def clear_box(key, subkey=Any):
        match subkey:
            case x if x == Any:
                _DootPostBox.boxes[key][_DootPostBox.default_subkey] = []
            case None:
                _DootPostBox.boxes[key] = defaultdict(list)
            case _:
                _DootPostBox.boxes[key][subkey] = []

@doot.check_protocol
class PutPostAction(Action_p):
    """
      push data to the inter-task postbox of this task tree
      The arguments of the action are held in self.spec
      'args' are pushed to the default subbox
      'kwargs' are pushed to the kwarg subbox
    """
    _toml_kwargs = ["args", "kwargs"]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        target = TASK_NAME.to_type(spec, task_state).root()
        for statekey in spec.args:
            data = DootKey.make(statekey).to_type(spec, task_state)
            _DootPostBox.put(target, data)

        for subkey,statekey in spec.kwargs.items():
            data = DootKey.make(statekey).to_type(spec, task_state)
            _DootPostBox.put(target, data, subkey=subkey)


@doot.check_protocol
class GetPostAction(Action_p):
    """
      Read data from the inter-task postbox of a task tree
      The arguments of the action are held in self.spec

      from=task
      kwarg=subkey -> get the subbox and update task state as kwarg
      kwarg=""     -> get the default subbox
      kwarg="*"    -> get the entire box dict
    """
    _toml_kwargs = [FROM_KEY]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        task_root = TASK_NAME.to_type(spec, task_state).root()
        from_task = FROM_KEY.to_type(spec, task_state, type_=str|None)
        target_box = from_task or task_root

        updates = {}
        for key,subkey in spec.kwargs.items():
            if key == FROM_KEY:
                pass
            actual_key = DootKey.make(key, explicit=True).expand(spec, task_state)
            if subkey == "" or subkey == "-":
                updates[actual_key] = _DootPostBox.get(target_box, subkey=Any)
            elif subkey == "*":
                updates[actual_key] = _DootPostBox.get(target_box, subkey=None)
            else:
                updates[actual_key] = _DootPostBox.get(target_box, subkey=subkey)

        return updates

@doot.check_protocol
class ClearPostAction(Action_p):
    """
      Clear your postbox
    """
    _toml_kwargs = [FROM_KEY, SUBKEY]

    def __call__(self, spec, state):
        from_task = TASK_NAME.to_type(spec, state).root()
        subkey    = SUBKEY.expand(spec, state, on_fail=Any)
        _DootPostBox.clear_box(from_task, subkey=subkey)
        return


@doot.check_protocol
class SummarizePostAction(Action_p):
    """
      print a summary of this task tree's postbox
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = [FROM_KEY, "full"]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        from_task = FROM_KEY.to_type(spec, task_state, type_=str|None) or TASK_NAME.to_type(spec, task_state).root()
        data   = _DootPostBox.get(from_task)
        if spec.kwargs.on_fail(False, bool).full():
            for x in data:
                printer.info("Postbox %s: Item: %s", from_task, str(x))

        printer.info("Postbox %s: Size: %s", from_task, len(data))
