#!/usr/bin/env python3
"""

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
from dataclasses import InitVar, dataclass, field, _MISSING_TYPE
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1

##-- end builtin imports

from doot._structs.action_spec import ActionSpec
from doot._structs.artifact import TaskArtifact
from doot._structs.code_ref import CodeReference
from doot._structs.location import Location
from doot._structs.param_spec import ParamSpec
from doot._structs.stub import TaskStub, TaskStubPart
from doot._structs.task_name import TaskName
from doot._structs.task_spec import TaskSpec
from doot._structs.trace import TraceRecord

from doot._structs.dkey import DKey
from doot.utils.dkey_decorator import DKeyed
