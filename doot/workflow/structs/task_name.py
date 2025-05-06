#!/usr/bin/env python3
"""

"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import weakref
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from pydantic import field_validator, model_validator
from jgdv import Maybe
from jgdv.structs.strang import Strang
from jgdv.mixins.enum_builders import FlagsBuilder_m

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors

# ##-- end 1st party imports

from .. import _interface as API # noqa: N812

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe, VerStr
    from jgdv.structs.strang import Strang_p
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from .._interface import TaskName_p
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging
DEFAULT_SEP : Final[str] = doot.constants.patterns.TASK_SEP # type: ignore

##--|
class _TaskNameOps_m:
    """ Operations Mixin for manipulating TaskNames """

    @classmethod
    def pre_process[T:type[Strang_p]](cls:T, data:str, *, strict:bool=False) -> T:
        """ Remove 'tasks' as a prefix, and strip quotes  """
        match data:
            case str() if not strict and data.startswith("tasks."):
                data = data.removeprefix("tasks.")
            case _:
                pass

        return super().pre_process(data).replace('"', "") # type: ignore

    def match_version(self, other:str|Strang|VerStr) -> bool:
        """ match version constraints of two task names against each other """
        raise NotImplementedError()

    @classmethod
    def from_parts[T:type[TaskName_p]](cls:T, group:str, body:str) -> T: # type: ignore
        return cls(f"{group}{cls._separator}{body}") # type: ignore

    def with_cleanup(self:TaskName_p) -> TaskName_p:
        if self.is_cleanup():
            return self
        return self.push(API.CLEANUP_MARKER)

    def is_cleanup(self:TaskName_p) -> bool:
        return API.CLEANUP_MARKER in self


class TaskName(_TaskNameOps_m, Strang):
    """
      A Task Name.
    """

    _separator          : ClassVar[str]           = DEFAULT_SEP

    @ftz.cached_property
    def readable(self) -> str:
        """ format this name to a readable form
        ie: elide uuids as just <UUID>
        """
        group = self[0:]
        tail = self._subseparator.join([x if "<uuid" not in x else "<UUID>" for x in self.body()])
        return f"{group}{self._separator}{tail}"
