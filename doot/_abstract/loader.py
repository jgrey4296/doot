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

    def setup(self, opt_values) -> None:
        raise NotImplementedError()

    def load(self, cmd, pos_args) -> list:
        raise NotImplementedError()

class TaskLoader_i(Loader_i):
    cmd_options      : list
    _task_collection : list
    _build_failures  : list
    _task_class      : type

    @classmethod
    def build(cls, config:Tomler):
        return cls(config)

    def __init__(self, config):
        # list of command names, used to detect clash of task names and commands
        self.cmd_names = []
        self.config    = None   # reference to config object taken from Command
        self.task_opts = None  # dict with task options (no need parsing, API usage)

class ConfigLoader_i(Loader_i):
    FRONTEND_PLUGIN_TYPES : Final = ['command', 'reporter', 'action', 'tasker', 'task', 'group' ]
    BACKEND_PLUGIN_TYPES  : Final = ['database', 'control', 'dispatch', 'runner', 'loader', 'parser']

    @classmethod
    def build(cls, arg_list, extra, filenames):
        return cls(arg_list, extra, filenames)

class CommandLoader_i(Loader_i):

    @classmethod
    def build(cls, config:Tomler, cmds:list):
        return cls(config, cmds)
