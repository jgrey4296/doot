## base_action.py -*- mode: python -*-
"""
  Postbox: Each Task Tree gets one, as a set[Any]
  Each Task can put something in its own postbox.
  And can read any other task tree's postbox, but not modify it.

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from collections import defaultdict
from time import sleep
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import sh

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot._abstract import Action_p
from doot.errors import DootTaskError, DootTaskFailed
from doot.structs import DKey, TaskName, DKeyed

# ##-- end 1st party imports

logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
STATE_TASK_NAME_K : Final[str] = doot.constants.patterns.STATE_TASK_NAME_K

##-- expansion keys
UPDATE      : Final[DKey] = DKey("update_")
TASK_NAME   : Final[DKey] = DKey(STATE_TASK_NAME_K)
SUBKEY      : Final[DKey] = DKey("subkey")
##-- end expansion keys

class _DootPostBox:
    """
      Internal Postbox class.
      holds a static variable of `boxes`, which maps task roots -> unique postbox
      Postboxes are lists, values are appended to it

      Can 'put', 'get', 'clear_box', and 'clear'.

      Keys are task names, of {body}..{tail}
      eg: example::task..key
      which corresponds to body[example::task][key]
    """

    boxes : ClassVar[dict[str,list[Any]]] = defaultdict(lambda: defaultdict(list))

    default_subkey                        = "-"
    whole_box_key                         = "*"

    @staticmethod
    def put(key:TaskName, val):
        if not key.has_root():
            raise ValueError("Tried to use a postbox key with no subkey", key)
        subbox = str(key.last())
        box    = str(key.root())
        match val:
            case None | [] | {} | dict() if not bool(val):
                pass
            case list() | set():
                _DootPostBox.boxes[box][subbox] += val
            case _:
                _DootPostBox.boxes[box][subbox].append(val)

    @staticmethod
    def get(key:TaskName) -> list|dict:
        if not key.has_root():
            raise ValueError("tried to get from postbox with no subkey", key)
        box    = str(key.root())
        subbox = str(key.last())
        match subbox:
            case "*" | None:
                return _DootPostBox.boxes[box].copy()
            case _:
                return _DootPostBox.boxes[box][subbox][:]

    @staticmethod
    def clear_box(key):
        if not key.has_root():
            raise ValueError("tried to clear a box without a subkey", key)
        box    = str(key.root())
        subbox = str(key.last())
        match subbox:
            case x if x == _DootPostBox.whole_box_key:
                _DootPostBox.boxes[box] = defaultdict(list)
            case _:
                _DootPostBox.boxes[box][subkey] = []

    @staticmethod
    def clear():
        _DootPostBox.boxes.clear()

class PutPostAction(Action_p):
    """
    push data to the inter-task postbox of this task tree
    The arguments of the action are held in self.spec
    'args' are pushed to the default subbox
    'kwargs' are pushed to the kwarg specific subbox

    eg: {do="post.put", args=["{key}", "{key}"], "group::task.sub..subbox"="{key}"}
    """

    @DKeyed.args
    @DKeyed.kwargs
    @DKeyed.taskname
    def __call__(self, spec, state, args, kwargs, _basename) -> dict|bool|None:
        logging.debug("PostBox Put: %s : args(%s) : kwargs(%s)", _basename, args, list(kwargs.keys()))
        target = _basename.root().subtask(_DootPostBox.default_subkey)
        for statekey in args:
            data = DKey(statekey).expand(spec, state)
            _DootPostBox.put(target, data)

        for box_str,statekey in kwargs.items():
            try:
                box = TaskName.build(box_str)
            except ValueError:
                box = _basename.root(top=True).subtask(box_str)
            match statekey:
                case str():
                    data = DKey(statekey).expand(spec, state)
                    _DootPostBox.put(box, data)
                case [*xs]:
                    for x in statekey:
                        data = DKey(x).expand(spec, state)
                        _DootPostBox.put(box, data)

class GetPostAction(Action_p):
    """
      Read data from the inter-task postbox of a task tree
      The arguments of the action are held in self.spec

      stateKey="group::task.sub..{subbox}"
      eg: data="bib::format..-"
    """

    @DKeyed.kwargs
    def __call__(self, spec, state, kwargs) -> dict|bool|None:
        updates = {}
        for key,box_str in kwargs.items():
            state_key          = DKey(key, explicit=True).expand(spec, state)
            target_box         = TaskName.build(box_str)
            updates[state_key] = _DootPostBox.get(target_box)

        return updates

class ClearPostAction(Action_p):
    """
      Clear your postbox
    """

    @DKeyed.formats("key", fallback=Any)
    @DKeyed.taskname
    def __call__(self, spec, state, key, _basename):
        from_task = _basename.root(top=True).subtask(key)
        _DootPostBox.clear_box(from_task)
        return

class SummarizePostAction(Action_p):
    """
      print a summary of this task tree's postbox
      The arguments of the action are held in self.spec
    """

    @DKeyed.types("from", check=str|None)
    @DKeyed.types("full", check=bool, fallback=False)
    def __call__(self, spec, state, _from, full) -> dict|bool|None:
        from_task = _from or TASK_NAME.expand(spec, state).root(top=True)
        data   = _DootPostBox.get(from_task)
        if full:
            for x in data:
                printer.info("Postbox %s: Item: %s", from_task, str(x))

        printer.info("Postbox %s: Size: %s", from_task, len(data))
