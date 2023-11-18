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
from doot.utils.string_expand import expand_str, expand_key

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
            path_str = expand_str(val, spec, task_state)
            result[kwarg] = self.import_callable(path_str)

        return result



@doot.check_protocol
class PushState(Action_p):
    """
      task_state[update_] += [task_state[x] for x in spec.args]
    """
    _toml_kwargs = ["update_"]

    def __call__(self, spec, task_state) -> dict|bool|None:
        data_key = expand_str(spec.kwargs.update_, spec, task_state)
        data = list(task_state.get(data_key, []))

        for arg in spec.args:
            match task_state[arg]:
                case list() as x:
                    data += x
                case _:
                    data.append(expand_str(x, spec, task_state))

        return { data_key : data }


@doot.check_protocol
class AddNow(Action_p):

    _toml_kwargs = ["format", "update_"]

    def __call__(self, spec, state):
        data_key = spec.kwargs.on_fail("_date").update_()
        format = expand_key(spec.kwargs.on_fail("format").format_(), spec, state)
        now = datetime.datetime.now()
        return { data_key : now.strftime(format) }
