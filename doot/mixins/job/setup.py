#!/usr/bin/env python3
"""


See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


from collections import defaultdict
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.errors import DootDirAbsent, DootTaskError
from doot.structs import DootTaskSpec, DootTaskName, DootCodeReference, DootActionSpec


class SetupMixin:
    """
      A terse mixin to add a single setup task before all subtasks/head of this job
    """

    @classmethod
    def stub_class(cls, stub):
        stub['setup_actions'].set(type="list[dict]",   default=[])

    def build(self, **kwargs):
        entry_task = self._build_setup(kwargs)
        for task in super().build(**kwargs):
            match task:
                case None:
                    pass
                case DootTaskSpec():
                    task.depends_on.append(entry_task.name)
                    yield task

        yield entry_task


    def _build_setup(self, kwargs) -> DootTaskSpec:
        inject_keys = set(self.spec.inject)
        inject_dict = {k: self.spec.extra[k] for k in inject_keys}
        kwargs.update(inject_dict)
        setup = self.default_task("$entry$", kwargs)
        spec_setup_actions     = [DootActionSpec.from_data(x) for x in self.spec.extra.on_fail([], list).setup_actions()]
        setup.actions         += spec_setup_actions
        setup.priority        += self.spec.priority

        return setup
