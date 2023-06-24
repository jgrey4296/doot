#!/usr/bin/env python3
"""

"""
##-- imports
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

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class Loader_i:

    def setup(self, *args, **kwargs) -> None:
        raise NotImplementedError()

    def load(self) -> Tomler:
        raise NotImplementedError()

class PluginLoader_i(Loader_i):
    """ Base for the first things loaded: plugins."""

    def setup(self, extra_config:Tomler):
        raise NotImplementedError()

class CommandLoader_i(Loader_i):
    """ Base for the second thing loaded: commands """

    def setup(self, plugins:dict):
        raise NotImplementedError()

class TaskLoader_i(Loader_i):
    """ Base for the final thing loaded: user tasks """
    _task_collection : list
    _build_failures  : list
    _task_class      : type

    def setup(self, plugins:dict):
        raise NotImplementedError()
