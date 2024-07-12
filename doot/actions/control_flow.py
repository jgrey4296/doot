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

from doot.structs import DKey, CodeReference, DKeyed
from doot.mixins.path_manip import PathManip_m
from doot.actions.base_action import DootBaseAction
from doot.utils.action_decorators import ControlFlow

@ControlFlow()
class PredicateCheck(DootBaseAction):
    """
      Get a predicate using the kwarg `pred`,
      call it with the action spec and task state.
      return its result for the task runner to handle

    """

    @DKeyed.references("pred")
    def __call__(self, spec, state, _pred) -> dict|bool|None:
        predicate = _pred.try_import()
        return predicate(spec,state)

@ControlFlow()
class FileExistsCheck(DootBaseAction):
    """ Continue only if a file exists. invertable with `not`.
      converts to a failure instead of skip with fail=true
      """

    @DKeyed.args
    @DKeyed.types("not", check=bool, fallback=False)
    @DKeyed.types("fail", check=bool, fallback=False)
    def __call__(self, spec, state, args, _invert, _fail) -> dict|bool|None:
        fail    = self.ActRE.FAIL if _fail else self.ActRE.SKIP

        for arg in args:
            path = DKey(arg, explicit=True, mark=DKey.mark.PATH).expand(spec, state, on_fail=None)
            exists = bool(path and path.exists())
            if _invert:
                exists = not exists
            match exists:
                case True:
                    continue
                case False:
                    return fail

        return None

@ControlFlow()
class SuffixCheck(DootBaseAction):
    """ Continue only if args ext is in supplied extensions
      invertable, failable
      """

    @DKeyed.args
    @DKeyed.types("exts", check=list)
    @DKeyed.types("not", check=bool, fallback=False)
    @DKeyed.types("fail", check=bool, fallback=False)
    def __call__(self, spec, state, args, exts, _invert, _fail):
        result = self.ActRE.SKIP
        if _fail:
            result = self.ActRE.FAIL

        for arg in args:
            path = DKey(arg, explicit=True, mark=DKey.mark.PATH).expand(spec, state, on_fail=None)
            match path.suffix in exts, _invert:
                case False, True:
                    continue
                case False, False:
                    return result
                case True, True:
                    return result
                case True, False:
                    continue

@ControlFlow()
class RelativeCheck(PathManip_m, DootBaseAction):
    """ continue only if paths are relative to a base.
      invertable. Skips by default, can fail
    """

    @DKeyed.args
    @DKeyed.types("bases", check=list)
    @DKeyed.types("not", check=bool, fallback=False)
    @DKeyed.types("fail", check=bool, fallback=False)
    def __call__(self, spec, state, args, _bases, _invert, _fail):
        result = self.ActRE.SKIP
        if _fail:
            result = self.ActRE.SKIP

        roots = self._build_roots(spec, state, _bases)
        try:
            for arg in args:
                path = DKey(arg, explicit=True, mark=DKey.mark.PATH).expand(spec, state, on_fail=None)
                match self._get_relative(path, roots), _invert:
                    case None, True:
                        return
                    case None, False:
                        return result
                    case _, True:
                        return result
                    case _, False:
                        return
        except ValueError:
            return result

class LogAction(DootBaseAction):

    @DKeyed.types("level", check=str, fallback="INFO")
    @DKeyed.formats("msg")
    def __call__(self, spec, state, level, msg):
        level        = logmod.getLevelName(level)
        printer.log(level, msg)

@ControlFlow()
class StalenessCheck(DootBaseAction):
    """ Skip the rest of the task if old hasn't been modified since new was modifed """

    @DKeyed.paths("old", "new")
    def __call__(self, spec, state, old, new) -> dict|bool|None:
        if new.exists() and (old.stat().st_mtime_ns <= new.stat().st_mtime_ns):
            return self.ActRE.SKIP

@ControlFlow()
class AssertInstalled(DootBaseAction):
    """
    Easily check a program can be found and used
    """

    @DKeyed.args
    @DKeyed.types("env", fallback=sh, check=sh.Command|None)
    def __call__(self, spec, state, args, env) -> dict|bool|None:
        failures = []
        for prog in args:
            try:
                getattr(env, prog)
            except sh.CommandNotFound:
                failures.append(prog)

        if not bool(failures):
            return

        printer.exception("Required Programs were not found: %s", ", ".join(failures))
        return self.ActRE.FAIL

@ControlFlow()
class WaitAction:
    """ An action that waits for some amount of time """

    @DKeyed.types("count")
    def __call__(self, spec, state, count):
        sleep(count)
