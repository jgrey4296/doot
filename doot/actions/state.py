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
from doot.structs import CodeReference, DootKey

# ##-- end 1st party imports

printer = logmod.getLogger("doot._printer")

class AddStateAction(Action_p):
    """
      add to task state in the task description toml,
      adds kwargs directly, without expansion
    """

    @DootKey.dec.kwargs
    def __call__(self, spec, state:dict, kwargs) -> dict|bool|None:
        result = {}
        for k,v in kwargs.items():
            key = DootKey.build(v, explicit=True)
            val = key.to_type(spec, state)
            result[k] = val
        return result

class AddStateFn(Action_p):
    """ for each toml kwarg, import its value and set the state[kwarg] = val
      with expansion
    """

    @DootKey.dec.kwargs
    def __call__(self, spec, state:dict, kwargs) -> dict|bool|None:
        result = {}
        for kwarg, val in kwargs:
            key = DootKey.build(val, explicit=True)
            val = key.expand(spec, state)
            ref = CodeReference.build(val)
            result[kwarg] = ref.try_import()

        return result

class PushState(Action_p):
    """
      state[update_] += [state[x] for x in spec.args]
    """

    @DootKey.dec.args
    @DootKey.dec.redirects("update_")
    def __call__(self, spec, state, args, _update) -> dict|bool|None:
        data     = data_key.to_type(spec, state, type_=list|set|None, on_fail=[])

        arg_keys = (DootKey.build(arg, explicit=True).to_type(spec, state) for arg in args)
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

    @DootKey.dec.expands("format")
    @DootKey.dec.redirects("update_")
    def __call__(self, spec, state, format, _update):
        now      = datetime.datetime.now()
        return { _update : now.strftime(format) }

class PathParts(PathManip_m):
    """ take a path and add fstem, fpar, fname to state """

    @DootKey.dec.paths("from")
    @DootKey.dec.types("roots")
    @DootKey.dec.returns("fstem", "fpar", "fname", "fext", "pstem")
    def __call__(self, spec, state, _from, roots):
        root_paths = self._build_roots(spec, state, roots)
        return self._calc_path_parts(_from, root_paths)

class ShadowPath(PathManip_m):

    @DootKey.dec.paths("shadow_root")
    @DootKey.dec.types("base", hint={"type_":pl.Path})
    def __call__(self, spec, state, shadow_root, base):
        shadow_dir = self._shadow_path(base, shadow_root)
        return { "shadow_path" : shadow_dir }
