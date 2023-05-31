#!/usr/bin/env python3
"""

"""
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

import doot
from doot._abstract.cmd import DootCommand_i
from doot._abstract.parser import DootParamSpec
from collections import defaultdict

class StubCmd(DootCommand_i):
    _name      = "stub"
    _help      = []

    @property
    def param_specs(self) -> list:
        return []

    def __call__(self, tasks:dict, plugins:dict):
        # TODO interactively build a stub tasker
        raise NotImplementedError()
