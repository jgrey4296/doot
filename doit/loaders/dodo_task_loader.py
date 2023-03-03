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

from .namespace_task_loader import NamespaceTaskLoader

#### options related to dodo.py
# select dodo file containing tasks
opt_dodo = {
    'section': 'task loader',
    'name': 'dodoFile',
    'short': 'f',
    'long': 'file',
    'type': str,
    'default': 'dodo.py',
    'env_var': 'DOIT_FILE',
    'help': "load task from dodo FILE [default: %(default)s]"
}


# cwd
opt_cwd = {
    'section': 'task loader',
    'name': 'cwdPath',
    'short': 'd',
    'long': 'dir',
    'type': str,
    'default': None,
    'help': ("set path to be used as cwd directory "
             "(file paths on dodo file are relative to dodo.py location).")
}

# seek dodo file on parent folders
opt_seek_file = {
    'section': 'task loader',
    'name': 'seek_file',
    'short': 'k',
    'long': 'seek-file',
    'type': bool,
    'default': False,
    'env_var': 'DOIT_SEEK_FILE',
    'help': ("seek dodo file on parent folders [default: %(default)s]")
}


class DodoTaskLoader(NamespaceTaskLoader):
    """default task-loader create tasks from a dodo.py file"""
    cmd_options = (opt_dodo, opt_cwd, opt_seek_file)

    def setup(self, opt_values):
        # lazily load namespace from dodo file per config parameters:
        self.namespace = dict(inspect.getmembers(loader.get_module(
            opt_values['dodoFile'],
            opt_values['cwdPath'],
            opt_values['seek_file'],
        )))
