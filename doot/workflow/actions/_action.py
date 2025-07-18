## base_action.py -*- mode: Py -*-
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
import time
import types
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Maybe, Proto

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from .._interface import Action_p, ActionResponse_e
from doot.errors import TaskError, TaskFailed

# ##-- end 1st party imports

from typing import override

if TYPE_CHECKING:
    from ..structs.action_spec import ActionSpec

logging = logmod.getLogger(__name__)

@Proto(Action_p)
class DootBaseAction:
    """
    The basic action, which just prints that the action was called
    Subclass this and override __call__ for your own actions.
    The arguments of the action are held in the passed in spec
    __call__ is passed a *copy* of the task's state dictionary
    """
    ActRE = ActionResponse_e

    @override
    def __str__(self):
        return "Base Action"

    def __call__(self, spec:ActionSpec, state:dict) -> Maybe[dict|bool]:
        logging.debug("Base Action Called: %s", state.get("count", 0))
        doot.report.gen.detail("Base Action Called: %s", state.get("count", 0))
        if spec.args:
            doot.report.gen.user(" ".join(spec.args))
        return { "count" : state.get("count", 0) + 1 }
