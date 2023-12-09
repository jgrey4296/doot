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
from doot.utils.string_expand import expand_str, expand_key

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

    _toml_kwargs = ["msg", "level"]

    def __call__(self, spec, task_state):
        level        = logmod.getLevelName(spec.kwargs.on_fail("INFO", str).level())
        msg          = expand_key(spec.kwargs.on_fail("msg").msg_(), spec, task_state)
        expanded_msg = expand_str(msg, spec, task_state)
        printer.log(level, "%s", expanded_msg)

@doot.check_protocol
class StalenessCheck(Action_p):
    _toml_kwargs = ["old_", "new_"]
    inState      = ["old", "new"]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        old_loc = expand_key(spec.kwargs.on_fail("old").old_(), spec, task_state, as_path=True)
        new_loc = expand_key(spec.kwargs.on_fail("new").new_(), spec, task_state, as_path=True)

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
