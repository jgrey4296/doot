#!/usr/bin/env python3
"""

"""
# ruff: noqa:

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
import collections
import contextlib
import hashlib
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref
import atexit # for @atexit.register
import faulthandler
# ##-- end stdlib imports

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
    from jgdv import Maybe, Traceback
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal, ContextManager
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from doot.control.tracker._interface import WorkflowTracker_p
    from doot.workflow._interface import Artifact_i, Task_p
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
type Handler = bool|type[ContextManager]|ContextManager
# Body:

@runtime_checkable
class RunnerHandlers_p(Protocol):

    def run_next_task(self) -> None: ...

    def handle_success[T:Maybe[Task_p|Artifact_i]](self, task:T) -> T: ...

    def handle_failure(self, failure:Exception) -> None: ...

    def notify_artifact(self, art:Artifact_i) -> None: ...

    def sleep_after(self, task:Maybe[Task_p|Artifact_i]) -> None: ...

@runtime_checkable
class WorkflowRunner_p(Protocol):
    """
    Run tasks, actions, and jobs
    """

    def __init__(self, *, tracker:WorkflowTracker_p): ...
    def __call__(self, *tasks:str, handler:Maybe[Handler]=None) -> bool: ...
    def __enter__(self) -> Self: ...

    def __exit__(self, etype:Maybe[type], err:Maybe[Exception], tb:Maybe[Traceback]) -> bool: ...
