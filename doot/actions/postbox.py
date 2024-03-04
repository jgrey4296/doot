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
STATE_TASK_NAME_K : Final[str] = doot.constants.patterns.STATE_TASK_NAME_K

##-- expansion keys
FROM_KEY    : Final[DootKey] = DootKey.make("from")
UPDATE      : Final[DootKey] = DootKey.make("update_")
TASK_NAME   : Final[DootKey] = DootKey.make(STATE_TASK_NAME_K)
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
    def put(key:DootTaskName, val):
        subbox = key.last()
        box    = key.root()
        match val:
            case None | [] | {} | dict() if not bool(val):
                pass
            case list() | set():
                _DootPostBox.boxes[box][subbox] += val
            case _:
                _DootPostBox.boxes[box][subbox].append(val)

    @staticmethod
    def get(key:DootTaskName, subkey=Any) -> list:
        box    = key.root()
        subbox = key.last()
        match subbox:
            case "" | "-":
                return _DootPostBox.boxes[box][_DootPostBox.default_subkey][:]
            case x if x == Any:
                return _DootPostBox.boxes[box][_DootPostBox.default_subkey][:]
            case "*" | None:
                return _DootPostBox.boxes[box].copy()
            case _:
                return _DootPostBox.boxes[box][subbox]

    @staticmethod
    def clear_box(key):
        box    = key.root()
        subbox = key.last()
        match subbox:
            case x if x == Any:
                _DootPostBox.boxes[box][_DootPostBox.default_subkey] = []
            case False:
                _DootPostBox.boxes[box] = defaultdict(list)
            case _:
                _DootPostBox.boxes[box][subkey] = []

@doot.check_protocol
class PutPostAction(Action_p):
    """
    push data to the inter-task postbox of this task tree
    The arguments of the action are held in self.spec
    'args' are pushed to the default subbox
    'kwargs' are pushed to the kwarg subbox

    eg: {do="post.put", args=["{key}", "{key}"], subbox="{key}"}
    """

    @DootKey.kwrap.args
    @DootKey.kwrap.kwargs
    @DootKey.kwrap.taskname
    def __call__(self, spec, state, args, kwargs, _basename) -> dict|bool|None:
        target = basename.root().subtask(True)
        for statekey in args:
            data = DootKey.make(statekey).to_type(spec, state)
            _DootPostBox.put(target, data)

        for box,statekey in kwargs.items():
            box  = basename.root().subtask(box)
            data = DootKey.make(statekey).to_type(spec, state)
            _DootPostBox.put(box, data)


@doot.check_protocol
class GetPostAction(Action_p):
    """
      Read data from the inter-task postbox of a task tree
      The arguments of the action are held in self.spec

      stateKey="group::task.{subbox}"
      eg: data="bib::format.-"
    """

    @DootKey.kwrap.kwargs
    def __call__(self, spec, state, _from, kwargs) -> dict|bool|None:
        updates = {}
        for key,subkey in kwargs.items():
            if key == FROM_KEY:
                pass
            state_key          = DootKey.make(key, explicit=True).expand(spec, state)
            target_box         = DootTaskName.from_str(subkey)
            updates[state_key] = _DootPostBox.get(target_box)

        return updates

@doot.check_protocol
class ClearPostAction(Action_p):
    """
      Clear your postbox
    """
    _toml_kwargs = [FROM_KEY, SUBKEY]

    @DootKey.kwrap.expands("subkey", hint={"on_fail":Any})
    def __call__(self, spec, state, subkey):
        from_task = TASK_NAME.to_type(spec, state).root()
        _DootPostBox.clear_box(from_task, subkey=subkey)
        return


@doot.check_protocol
class SummarizePostAction(Action_p):
    """
      print a summary of this task tree's postbox
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = [FROM_KEY, "full"]

    @DootKey.kwrap.types("from", hint={"type_":str|None})
    @DootKey.kwrap.types("full", hint={"type_":bool, "on_fail":False})
    def __call__(self, spec, state, _from, full) -> dict|bool|None:
        from_task = _from or TASK_NAME.to_type(spec, state).root()
        data   = _DootPostBox.get(from_task)
        if full:
            for x in data:
                printer.info("Postbox %s: Item: %s", from_task, str(x))

        printer.info("Postbox %s: Size: %s", from_task, len(data))
