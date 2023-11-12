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
import sh
import shutil
import doot
from doot.errors import DootTaskError, DootTaskFailed
from doot._abstract import Action_p
from doot.mixins.importer import ImporterMixin

@doot.check_protocol
class AddStateAction(Action_p):
    """
      add to task state in the task description toml
    """
    _toml_kwargs = ["<Any>"]

    def __str__(self):
        return f"Base Action: {self.spec.args}"

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        return dict(spec.kwargs)


@doot.check_protocol
class AddStateFn(Action_p, ImporterMixin):
    """ for each toml kwarg, import its value and set the task_state[kwarg] = val """

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        result = {}
        for kwarg, val in spec.kwargs:
            result[kwarg] = self.import_class(val)

            pass
        return result



@doot.check_protocol
class PushState(Action_p):
    """
      task_state[target] += [task_state[x] for x in spec.args]
    """
    _toml_kwargs = ["target"]

    def __call__(self, spec, task_state) -> dict|bool|None:
        data = list(task_state.get(spec.kwargs.target, []))

        for arg in spec.args:
            match task_state[arg]:
                case list() as x:
                    data += x
                case _:
                    data.append(x)

        return { spec.kwargs.target : data }
