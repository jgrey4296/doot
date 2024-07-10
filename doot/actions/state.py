## base_action.py -*- mode: python -*-
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
import shutil
import time
import types
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
from doot.actions.job_injection import (JobInjectPathParts,
                                        JobInjectShadowAction)
from doot.errors import DootTaskError, DootTaskFailed
from doot.mixins.path_manip import PathManip_m
from doot.structs import CodeReference, DKey, DKeyed

# ##-- end 1st party imports

printer = logmod.getLogger("doot._printer")

class AddStateAction(Action_p):
    """
      add to task state in the task description toml,
      adds kwargs directly, without expansion
    """

    @DKeyed.kwargs
    def __call__(self, spec, state:dict, kwargs) -> dict|bool|None:
        result = {}
        for k,v in kwargs.items():
            key = DKey(v, explicit=True)
            val = key.expand(spec, state)
            result[k] = val
        return result

class AddStateFn(Action_p):
    """ for each toml kwarg, import its value and set the state[kwarg] = val
      with expansion
    """

    @DKeyed.kwargs
    def __call__(self, spec, state:dict, kwargs) -> dict|bool|None:
        result = {}
        for kwarg, val in kwargs:
            key = DKey(val, explicit=True)
            val = key.expand(spec, state)
            ref = CodeReference.build(val)
            result[kwarg] = ref.try_import()

        return result

class PushState(Action_p):
    """
      state[update_] += [state[x] for x in spec.args]
    """

    @DKeyed.args
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, args, _update) -> dict|bool|None:
        data     = data_key.expand(spec, state, check=list|set|None, fallback=[])

        arg_keys = (DKey(arg, explicit=True).expand(spec, state) for arg in args)
        to_add   = map(lambda x: x if isinstance(x, list) else [x],
                       filter(lambda x: x is not None, arg_keys))

        match data:
            case set():
                list(map(lambda x: data.update(x), to_add))
            case list():
                list(map(lambda x: data.extend(x), to_add))

        return { _update : data }

class AddNow(Action_p):
    """
      Add the current date, as a string, to the state
    """

    @DKeyed.expands("format")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, format, _update):
        now      = datetime.datetime.now()
        return { _update : now.strftime(format) }

class PathParts(PathManip_m):
    """ take a path and add fstem, fpar, fname to state """

    @DKeyed.paths("from")
    @DKeyed.types("roots")
    @DKeyed.returns("fstem", "fpar", "fname", "fext", "pstem")
    def __call__(self, spec, state, _from, roots):
        root_paths = self._build_roots(spec, state, roots)
        return self._calc_path_parts(_from, root_paths)

class ShadowPath(PathManip_m):

    @DKeyed.paths("shadow_root")
    @DKeyed.types("base", check=pl.Path)
    def __call__(self, spec, state, shadow_root, base):
        shadow_dir = self._shadow_path(base, shadow_root)
        return { "shadow_path" : shadow_dir }
