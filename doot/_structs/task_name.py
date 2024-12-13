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
import types
import weakref
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Self, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
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

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

CLEANUP_MARKER : Final[str] = "$cleanup$"

class _TaskNameOps_m:
    """ Operations Mixin for manipulating TaskNames """

    @classmethod
    def pre_process(cls, data:str, *, strict=False) -> str:
        """ Remove 'tasks' as a prefix, and strip quotes  """
        match data:
            case str() if not strict and data.startswith("tasks."):
                data = data.removeprefix("tasks.")
            case _:
                pass

        return super().pre_process(data).replace('"', "")

    def match_version(self, other) -> bool:
        """ match version constraints of two task names against each other """
        raise NotImplementedError()

    @classmethod
    def from_parts(cls, group, body) -> Self:
        return cls(f"{group}{cls._separator}{body}")

    def with_cleanup(self) -> Self:
        if self.is_cleanup():
            return self
        return self.push(CLEANUP_MARKER)

    def is_cleanup(self) -> bool:
        return CLEANUP_MARKER in self


class TaskName(_TaskNameOps_m, Strang):
    """
      A Task Name.
    """

    _separator          : ClassVar[str]           = doot.constants.patterns.TASK_SEP

    @ftz.cached_property
    def readable(self) -> str:
        """ format this name to a readable form
        ie: elide uuids as just <UUID>
        """
        group = self[0:]
        tail = self._subseparator.join([str(x) if not isinstance(x, UUID) else "<UUID>" for x in self.body()])
        return "{}{}{}".format(group, self._separator, tail)
