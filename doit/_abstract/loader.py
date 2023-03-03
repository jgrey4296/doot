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


class TaskLoader():
    def __init__(self):
        raise NotImplementedError(
            'doit.cmd_base.py:TaskLoader was removed on 0.36.0, use TaskLoader2 instead')

class TaskLoader2():
    """Interface of task loaders with new-style API.

    :cvar cmd_options:
          (list of dict) see cmdparse.CmdOption for dict format

    This API separates the loading of the configuration and the loading
    of the actual tasks, which enables additional elements to be available
    during task creation.
    """
    API = 2
    cmd_options = ()

    def __init__(self):
        # list of command names, used to detect clash of task names and commands
        self.cmd_names = []
        self.config = None   # reference to config object taken from Command
        self.task_opts = None  # dict with task options (no need parsing, API usage)

    def setup(self, opt_values):
        """Delayed initialization.

        To be implemented if the data is needed by derived classes.

        :param opt_values: (dict) with values for cmd_options
        """
        pass

    def load_doit_config(self):
        """Load doit configuration.

        The method must not be called before invocation of ``setup``.

        :return: (dict) Dictionary of doit configuration values.
        """
        raise NotImplementedError()  # pragma: no cover

    def load_tasks(self, cmd, pos_args):
        """Load tasks.

        The method must not be called before invocation of ``load_doit_config``.

        :param cmd: (doit.cmd_base.Command) current command being executed
        :param pos_args: (list str) positional arguments from command line
        :return: (List[Task])
        """
        raise NotImplementedError()  # pragma: no cover
