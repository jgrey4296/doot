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

from doot.structs import DootKey, DootCodeReference
from doot.mixins.path_manip import PathManip_m
from doot.actions.base_action import DootBaseAction
from doot.utils.decorators import ControlFlow

##-- expansion keys
MSG          : Final[DootKey] = DootKey.build("msg")
OLD          : Final[DootKey] = DootKey.build("old")
NEW          : Final[DootKey] = DootKey.build("new")
LEVEL        : Final[DootKey] = DootKey.build("level")
PRED         : Final[DootKey] = DootKey.build("pred")
FILE_TARGET  : Final[DootKey] = DootKey.build("file")

##-- end expansion keys

@ControlFlow()
class CancelOnPredicateAction(DootBaseAction):
    """
      Get a predicate using the kwarg `pred`,
      call it with the action spec and task state.
      return its result for the task runner to handle

    """

    @DootKey.dec.references("pred")
    def __call__(self, spec, state, _pred) -> dict|bool|None:
        predicate = _pred.try_import()
        return predicate(spec,state)

@ControlFlow()
class SkipIfFileExists(DootBaseAction):

    @DootKey.dec.args
    def __call__(self, spec, state, args) -> dict|bool|None:
        for arg in args:
            key = DootKey.build(arg, explicit=True)
            path = key.to_path(spec, state, on_fail=None)
            if path and path.exists():
                printer.info("Target Exists: %s", path)
                return self.ActRE.SKIP

@ControlFlow()
class SkipUnlessSuffix(DootBaseAction):

    @DootKey.dec.paths("fpath")
    @DootKey.dec.expands("ext")
    def __call__(self, spec, state, fpath, ext):
        if fpath.suffix != ext:
            return self.ActRE.SKIP

class LogAction(DootBaseAction):

    @DootKey.dec.types("level", hint={"type_":str, "on_fail":"INFO"})
    @DootKey.dec.expands("msg")
    def __call__(self, spec, state, level, msg):
        level        = logmod.getLevelName(level)
        msg          = MSG.expand(spec, state, rec=True)
        printer.log(level, "%s", msg)

@ControlFlow()
class StalenessCheck(DootBaseAction):
    """ Skip the rest of the task if old hasn't been modified since new was modifed """

    @DootKey.dec.paths("old", "new")
    def __call__(self, spec, state, old, new) -> dict|bool|None:
        if new.exists() and (old.stat().st_mtime_ns <= new.stat().st_mtime_ns):
            return self.ActRE.SKIP

@ControlFlow()
class AssertInstalled(DootBaseAction):
    """
    Easily check a program can be found and used
    """

    @DootKey.dec.args
    def __call__(self, spec, state, args) -> dict|bool|None:
        failures = []
        for prog in args:
            try:
                getattr(sh, prog)
            except sh.CommandNotFound:
                failures.append(prog)

        if not bool(failures):
            return

        printer.exception("Required Programs were not found: %s", ", ".join(failures))
        return self.ActRE.FAIL

@ControlFlow()
class WaitAction:
    """ An action that waits for some amount of time """

    @DootKey.dec.types("count")
    def __call__(self, spec, state, count):
        sleep(count)

@ControlFlow()
class SkipWhenRelativeTo(PathManip_m, DootBaseAction):

    @DootKey.dec.paths("fpath")
    @DootKey.dec.types("when_roots")
    def __call__(self, spec, state, fpath, _roots):
        roots = self._build_roots(spec, state, _roots)
        try:
            match self._get_relative(fpath, roots):
                case None:
                    return
                case _:
                    return self.ActRE.SKIP
        except ValueError:
            return

@ControlFlow()
class SkipUnlessRelativeTo(PathManip_m, DootBaseAction):

    @DootKey.dec.paths("fpath")
    @DootKey.dec.types("unless_roots")
    def __call__(self, spec, state, fpath, _roots):
        roots = self._build_roots(spec, state, _roots)
        try:
            match self._get_relative(fpath, roots):
                case None:
                    return self.ActRE.SKIP
                case _:
                    return
        except ValueError:
            return self.ActRE.SKIP
