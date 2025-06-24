#!/usr/bin/env python3
"""

"""
# ruff: noqa:

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import atexit#  for @atexit.register
import collections
import contextlib
import datetime
import enum
import faulthandler
import functools as ftz
import hashlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 1st party imports
from doot.workflow._interface import (ArtifactStatus_e, Task_i, TaskStatus_e)

# ##-- end 1st party imports

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
    from doot.workflow._interface import (InjectSpec_i, ActionSpec_i,
                                          RelationSpec_i, TaskSpec_i)
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from jgdv import Maybe, Ident
    from jgdv.structs.chainguard import ChainGuard
    from doot.workflow._interface import Task_i, TaskName_p, Artifact_i

    type Abstract[T] = T
    type Concrete[T] = T
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class TaskFactory_p(Protocol):

    def __init__(self, *, spec_ctor:Maybe[type]=None, task_ctor:Maybe[type]=None, job_ctor:Maybe[type]=None): ...

    def build(self, data:ChainGuard|dict|TaskName_p|str) -> TaskSpec_i: ...

    def instantiate(self, obj:TaskSpec_i, *, extra:Maybe[Mapping|bool]=None) -> TaskSpec_i: ...

    def reify_partial(self, obj:TaskSpec_i, actual:TaskSpec_i) -> TaskSpec_i: ...

    def over(self, obj:TaskSpec_i, data:TaskSpec_i, suffix:Maybe[str|Literal[False]]=None) -> TaskSpec_i: ...

    def under(self, obj:TaskSpec_i, data:dict|TaskSpec_i, suffix:Maybe[str|Literal[False]]=None) -> TaskSpec_i: ...

    def make(self, obj:TaskSpec_i, *, ensure:Maybe=None, inject:Maybe[tuple[InjectSpec_i, Task_i]]=None, parent:Maybe[Task_i]=None) -> Task_i:  ...

    def action_group_elements(self, obj:TaskSpec_i) -> Iterable[ActionSpec_i|RelationSpec_i]: ...

@runtime_checkable
class SubTaskFactory_p(Protocol):

    def generate_names(self, obj:TaskSpec_i) -> list[TaskName_p]: ...

    def generate_specs(self, obj:TaskSpec_i) -> list[dict]: ...

##--| components
