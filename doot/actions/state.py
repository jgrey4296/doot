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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto, Mixin
import sh
from jgdv.structs.strang import CodeReference
from jgdv.mixins.path_manip import PathManip_m
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot._abstract import Action_p
from doot.errors import TaskError, TaskFailed
from doot.mixins.path_manip import PathManip_m
from doot.structs import DKey, DKeyed

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

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

# isort: on
# ##-- end types


@Proto(Action_p)
class AddStateAction:
    """
      add to task state in the task description toml,
      adds kwargs directly, without expansion
    """

    @DKeyed.kwargs
    def __call__(self, spec, state:dict, kwargs) -> dict|bool|None:
        result = {}
        for k,v in kwargs.items():
            key = DKey(v)
            val = key.expand(spec, state)
            result[k] = val
        return result

@Proto(Action_p)
class AddStateFn:
    """ for each toml kwarg, import its value and set the state[kwarg] = val
      with expansion
    """

    @DKeyed.kwargs
    def __call__(self, spec, state:dict, kwargs) -> dict|bool|None:
        result = {}
        for kwarg, val in kwargs:
            key = DKey(val)
            val = key.expand(spec, state)
            ref = CodeReference(val)
            result[kwarg] = ref()

        return result

@Proto(Action_p)
class PushState:
    """
      state[update_] += [state[x] for x in spec.args]
    """

    @DKeyed.args
    @DKeyed.types("update_", check=set|list, fallback=list)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, args, _data, _update) -> dict|bool|None:
        target_data = data.copy()
        to_add = []
        for x in args:
            match DKey(x).expand(spec, state):
                case None:
                    pass
                case list()|set() as xs:
                    to_add += xs
                case x:
                    to_add.append(x)

        match target_data:
            case set():
                target_data.update(to_add)
            case list():
                target_data.extend(to_add)
            case _:
                raise TypeError("Unknown state target to push to", type(target_data), _update)

        return { _update : target_data }

@Proto(Action_p)
class AddNow:
    """
      Add the current date, as a string, to the state
    """

    @DKeyed.expands("format")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, format, _update):
        now      = datetime.datetime.now()
        return { _update : now.strftime(format) }

@Proto(Action_p)
@Mixin(PathManip_m, allow_inheritance=True)
class PathParts:
    """ take a path and add fstem, fpar, fname to state """

    @DKeyed.paths("from")
    @DKeyed.types("roots")
    @DKeyed.returns("fstem", "fpar", "fname", "fext", "pstem", "rpath")
    def __call__(self, spec, state, _from, roots):
        root_paths = self._build_roots(spec, state, roots)
        return self._calc_path_parts(_from, root_paths)

@Proto(Action_p)
@Mixin(PathManip_m, allow_inheritance=True)
class ShadowPath:

    @DKeyed.paths("shadow_root")
    @DKeyed.types("base", check=pl.Path)
    def __call__(self, spec, state, shadow_root, base):
        shadow_dir = self._shadow_path(base, shadow_root)
        return { "shadow_path" : shadow_dir }
