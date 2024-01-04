## base_action.py -*- mode: python -*-
"""
Actions for task control flow.
ie: Early exit from a task if a file exists
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
# from uuid import UUID, uuid1
# from weakref import ref

##-- end imports

printer = logmod.getLogger("doot._printer")

from time import sleep
import sh
import shutil
import doot
from doot.errors import DootTaskError, DootTaskFailed
from doot._abstract import Action_p
from doot.mixins.importer import ImporterMixin
from doot.enums import ActionResponseEnum as ActRE
import doot.utils.expansion as exp

##-- expansion keys
MSG   : Final[exp.DootKey] = exp.DootKey("msg")
OLD   : Final[exp.DootKey] = exp.DootKey("old")
NEW   : Final[exp.DootKey] = exp.DootKey("new")
LEVEL : Final[exp.DootKey] = exp.DootKey("level")

##-- end expansion keys

@doot.check_protocol
class CancelOnPredicateAction(Action_p, ImporterMixin):
    """
      Get a predicate using the kwarg `pred`,
      call it with the action spec and task state.
      return its result for the task runner to handle

    """
    _toml_kwargs = ["<Any>"]
    inState      = ["pred"]

    def __str__(self):
        return f"Cancel On Predicate Action: {self.spec.args}"

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        predicate = self.import_class(spec.kwargs.pred)
        return predicate(spec,task_state)

@doot.check_protocol
class LogAction(Action_p):

    _toml_kwargs = [MSG, LEVEL]

    def __call__(self, spec, task_state):
        level_name   = LEVEL.to_type(spec, task_state, type_=str|None) or "INFO"
        level        = logmod.getLevelName(level_name)
        msg          = MSG.expand(spec, task_state, rec=True)
        printer.log(level, "%s", msg)

@doot.check_protocol
class StalenessCheck(Action_p):
    _toml_kwargs = [OLD, NEW]
    inState      = ["old", "new"]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        old_loc = OLD.to_path(spec, task_state)
        new_loc = NEW.to_path(spec, task_state)

        if new_loc.exists() and old_loc.stat().st_mtime_ns <= new_loc.stat().st_mtime_ns:
            return ActRE.SKIP

@doot.check_protocol
class AssertInstalled:
    """
    Easily check a program can be found and used
    """
    _toml_kwargs = ["prog", "version"]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        return ActRE.FAIL
