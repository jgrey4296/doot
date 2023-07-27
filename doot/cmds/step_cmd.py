#!/usr/bin/env python3
"""

"""
##-- imports

##-- end imports

##-- default imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end default imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging
printer = logmod.getLogger("doot._printer")

import doot
from doot._abstract import Command_i

class StepCmd(Command_i):
    """
    Standard doit run command, but step through tasks
    """
    name            = 'step'
    doc_purpose     = "Enter breakpoint just before execution of task"
    doc_description = ""
    doc_usage       = "[TASK ...]"

    @property
    def param_specs(self) -> list:
        return super().param_specs + []


    def __call__(self, tasks:Tomler, plugins:Tomler):

        pass
