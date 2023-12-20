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
from doot.structs import DootCodeReference
import doot.utils.expansion as exp

##-- expansion keys
UPDATE : Final[exp.DootKey] = exp.DootKey("update_")
FORMAT : Final[exp.DootKey] = exp.DootKey("format")

##-- end expansion keys

@doot.check_protocol
class AddStateAction(Action_p):
    """
      add to task state in the task description toml,
      adds kwargs directly, without expansion
    """
    _toml_kwargs = ["<Any>"]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        return dict(spec.kwargs)


@doot.check_protocol
class AddStateFn(Action_p, ImporterMixin):
    """ for each toml kwarg, import its value and set the task_state[kwarg] = val
      with expansion
    """

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        result = {}
        for kwarg, val in spec.kwargs:
            ref = DootCodeReference.from_str(exp.to_str(val, spec, task_state))
            result[kwarg] = ref.try_import()

        return result



@doot.check_protocol
class PushState(Action_p):
    """
      task_state[update_] += [task_state[x] for x in spec.args]
    """
    _toml_kwargs = [UPDATE]

    def __call__(self, spec, task_state) -> dict|bool|None:
        data_key = UPDATE.redirect(spec)
        data     = data_key.to_any(spec, task_state, type_=list|set|None) or []

        to_add   = map(lambda x: x if isinstance(x, list) else [x],
                       filter(lambda x: x is not None,
                              (exp.to_any(arg, spec, task_state) for arg in spec.args)))
        match data:
            case set():
                list(map(lambda x: data.update(x), to_add))
            case list():
                list(map(lambda x: data.extend(x), to_add))

        return { data_key : data }


@doot.check_protocol
class AddNow(Action_p):
    """
      Add the current date, as a string, to the state
    """

    _toml_kwargs = [FORMAT, UPDATE]

    def __call__(self, spec, state):
        data_key = UPDATE.redirect(spec)
        format   = FORMAT.expand(spec, state)
        now      = datetime.datetime.now()
        return { data_key : now.strftime(format) }
