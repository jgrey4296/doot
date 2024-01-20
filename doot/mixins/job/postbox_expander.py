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

from tomlguard import TomlGuard
import doot
import doot.constants
from doot.errors import DootDirAbsent
from doot.mixins.job.subtask import SubMixin
from doot.structs import DootTaskSpec, DootActionSpec, DootKey
from doot.actions.postbox import _DootPostBox

class PostBoxExpanderMixin(SubMixin):
    """
      A Job mixin to create subtasks for each entry in a retrieved postbox list
    """

    def __init__(self, spec):
        super().__init__(spec)
        self.task_key = spec.extra.postbox.task
        self.sub_key  = spec.extra.postbox.sub_key
        self.inject_key = spec.extra.postbox.inject_key
        self.flatten_data = spec.extra.on_fail(False, bool).postbox.flatten()

    def _build_subs(self) -> Generator[DootTaskSpec]:
        base = self.fullname
        result : list = _DootPostBox.get(self.task_key, subkey=self.sub_key)
        inject_keys = set(self.spec.inject)
        inject_dict = {k: self.spec.extra[k] for k in inject_keys}
        for i, data in enumerate(result):
            uname = base.subtask(i)
            if isinstance(data, dict) and self.flatten_data:
                data_inject = data
            else:
                data_inject = { self.inject_key : data }

            match self._build_subtask(i, uname, **data_inject, **inject_dict):
                case None:
                    pass
                case DootTaskSpec() as subtask:
                    yield subtask
                case _ as subtask:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))



    @classmethod
    def stub_class(cls, stub):
        stub['postbox'].set(type="dict", default={"inject_key": "data", "task": "", "sub_key":"-"}, priority=80, comment="the taskname and subbox to expand. option: flatten=bool")
