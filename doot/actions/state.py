## base_action.py -*- mode: python -*-
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
import datetime
import sh
import shutil
import doot
from doot.errors import DootTaskError, DootTaskFailed
from doot._abstract import Action_p
from doot.mixins.importer import ImporterMixin
from doot.structs import DootCodeReference, DootKey

##-- expansion keys
UPDATE : Final[DootKey] = DootKey.make("update_")
FORMAT : Final[DootKey] = DootKey.make("format")
FROM   : Final[DootKey] = DootKey.make("from")
##-- end expansion keys

@doot.check_protocol
class AddStateAction(Action_p):
    """
      add to task state in the task description toml,
      adds kwargs directly, without expansion
    """

    @DootKey.kwrap.kwargs
    def __call__(self, spec, state:dict, kwargs) -> dict|bool|None:
        result = {}
        for k,v in kwargs.items():
            key = DootKey.make(v, explicit=True)
            val = key.to_type(spec, state)
            result[k] = val
        return result


@doot.check_protocol
class AddStateFn(Action_p, ImporterMixin):
    """ for each toml kwarg, import its value and set the state[kwarg] = val
      with expansion
    """

    @DootKey.kwrap.kwargs
    def __call__(self, spec, state:dict, kwargs) -> dict|bool|None:
        result = {}
        for kwarg, val in kwargs:
            key = DootKey.make(val, explicit=True)
            val = key.expand(spec, state)
            ref = DootCodeReference.from_str(val)
            result[kwarg] = ref.try_import()

        return result



@doot.check_protocol
class PushState(Action_p):
    """
      state[update_] += [state[x] for x in spec.args]
    """
    _toml_kwargs = [UPDATE]

    @DootKey.kwrap.args
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, args, _update) -> dict|bool|None:
        data     = data_key.to_type(spec, state, type_=list|set|None, on_fail=[])

        arg_keys = (DootKey.make(arg, explicit=True).to_type(spec, state) for arg in args)
        to_add   = map(lambda x: x if isinstance(x, list) else [x],
                       filter(lambda x: x is not None, arg_keys))

        match data:
            case set():
                list(map(lambda x: data.update(x), to_add))
            case list():
                list(map(lambda x: data.extend(x), to_add))

        return { _update : data }


@doot.check_protocol
class AddNow(Action_p):
    """
      Add the current date, as a string, to the state
    """

    @DootKey.kwrap.expands("format")
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, format, _update):
        now      = datetime.datetime.now()
        return { _update : now.strftime(format) }


@doot.check_protocol
class PathParts(Action_p):
    """ take a path and add fstem, fpar, fname to state """

    @DootKey.kwrap.paths("from")
    @DootKey.kwrap.returns("fstem", "fpar", "fname")
    def __call__(self, spec, state, _from):
        fpath = _from
        name  = fpath.name
        stem  = fpath
        # This handles "a/b/c.tar.gz"
        while stem.stem != stem.with_suffix("").stem:
            stem = stem.with_suffix("")

        return { "fstem": stem.stem,
                 "fpar" : fpath.parent,
                 "fname": name,
                }
