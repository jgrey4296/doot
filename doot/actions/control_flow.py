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
from doot.structs import DootKey, DootCodeReference

##-- expansion keys
MSG          : Final[DootKey] = DootKey.make("msg")
OLD          : Final[DootKey] = DootKey.make("old")
NEW          : Final[DootKey] = DootKey.make("new")
LEVEL        : Final[DootKey] = DootKey.make("level")
PRED         : Final[DootKey] = DootKey.make("pred")
FILE_TARGET  : Final[DootKey] = DootKey.make("file")

##-- end expansion keys

@doot.check_protocol
class CancelOnPredicateAction(Action_p):
    """
      Get a predicate using the kwarg `pred`,
      call it with the action spec and task state.
      return its result for the task runner to handle

    """
    @DootKey.kwrap.expands("pred")
    def __call__(self, spec, state, pred) -> dict|bool|None:
        ref       = DootCodeReference.from_str(pred)
        predicate = ref.try_import()
        return predicate(spec,state)

@doot.check_protocol
class SkipIfFileExists(Action_p):

    @DootKey.kwrap.args
    def __call__(self, spec, state, args) -> dict|bool|None:
        for arg in args:
            key = DootKey.make(arg, explicit=True)
            path = key.to_path(spec, state, on_fail=None)
            if path and path.exists():
                printer.info("Target Exists: %s", path)
                return ActRE.SKIP

@doot.check_protocol
class LogAction(Action_p):

    @DootKey.kwrap.types("level", hint={"type_":str, "on_fail":"INFO"})
    @DootKey.kwrap.expands("msg")
    def __call__(self, spec, state, level, msg):
        level        = logmod.getLevelName(level_name)
        msg          = MSG.expand(spec, state, rec=True)
        printer.log(level, "%s", msg)

@doot.check_protocol
class StalenessCheck(Action_p):
    """ Skip the rest of the task if old hasn't been modified since new was modifed """

    @DootKey.kwrap.paths("old", "new")
    def __call__(self, spec, state, old, new) -> dict|bool|None:
        if new.exists() and (old.stat().st_mtime_ns <= new.stat().st_mtime_ns):
            return ActRE.SKIP

@doot.check_protocol
class AssertInstalled:
    """
    Easily check a program can be found and used
    """

    @DootKey.kwrap.args
    def __call__(self, spec, state, args) -> dict|bool|None:
        raise NotImplementedError()
        return ActRE.FAIL
