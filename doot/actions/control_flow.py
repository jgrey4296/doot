## base_action.py -*- mode: python -*-
"""
Actions for task control flow.
ie: Early exit from a task if a file exists
"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
# import abc
import datetime
# import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import shutil
import time
import types
from time import sleep

# ##-- end stdlib imports

# ##-- 3rd party imports
import sh
from jgdv import Proto, Mixin
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.actions.core.action import DootBaseAction
from doot.errors import TaskError, TaskFailed
from doot.mixins.path_manip import PathManip_m
from doot.structs import DKey, DKeyed
from doot.utils.action_decorators import ControlFlow

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class PredicateCheck(DootBaseAction):
    """
      Get a predicate using the kwarg `pred`,
      call it with the action spec and task state.
      return its result for the task runner to handle

    """

    @DKeyed.references("pred")
    def __call__(self, spec, state, _pred) -> dict|bool|None:
        predicate = _pred()
        return predicate(spec,state)

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
            path = DKey(arg, mark=DKey.Mark.PATH).expand(spec, state, on_fail=None)
            exists = bool(path and path.exists())
            if _invert:
                exists = not exists
            match exists:
                case True:
                    continue
                case False:
                    return fail

        return None

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
            path = DKey(arg, mark=DKey.Mark.PATH).expand(spec, state, on_fail=None)
            match path.suffix in exts, _invert:
                case False, True:
                    continue
                case False, False:
                    return result
                case True, True:
                    return result
                case True, False:
                    continue

@Mixin(PathManip_m, allow_inheritance=True)
class RelativeCheck(DootBaseAction):
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
                path = DKey(arg, mark=DKey.Mark.PATH).expand(spec, state, on_fail=None)
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
    """ A Basic log/print action  """

    @DKeyed.types("level", check=str, fallback="user")
    @DKeyed.formats("msg")
    @DKeyed.formats("target", fallback="task")
    def __call__(self, spec, state, level, msg, target):
        assert(msg is not None), "msg"
        doot.report.user(msg)

class StalenessCheck(DootBaseAction):
    """ Skip the rest of the task if old hasn't been modified since new was modifed """

    @DKeyed.paths("old", "new")
    def __call__(self, spec, state, old, new) -> dict|bool|None:
        if new.exists() and (old.stat().st_mtime_ns <= new.stat().st_mtime_ns):
            return self.ActRE.SKIP

class AssertInstalled(DootBaseAction):
    """
    Easily check a program can be found and used
    """

    @DKeyed.args
    @DKeyed.types("env", fallback=None, check=sh.Command|None)
    def __call__(self, spec, state, args, env) -> dict|bool|None:
        env = env or sh
        failures = []
        for prog in args:
            try:
                getattr(env, prog)
            except sh.CommandNotFound:
                failures.append(prog)

        if not bool(failures):
            return

        logging.exception("Required Programs were not found: %s", ", ".join(failures))
        return self.ActRE.FAIL

class WaitAction(DootBaseAction):
    """ An action that waits for some amount of time """

    @DKeyed.types("count")
    def __call__(self, spec, state, count):
        sleep(count)

class TriggerActionGroup(DootBaseAction):
    """ Trigger a non-standard action group """

    def __call__(self, spec, state):
        raise NotImplementedError()
