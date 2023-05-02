
#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import inspect
import logging as logmod
import pathlib as pl
import sys
from collections import OrderedDict
from copy import copy, deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from types import FunctionType, GeneratorType, MethodType
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

import importlib
from importlib.metadata import entry_points
import time
import doot
from doot._abstract.loader import TaskLoader_i, ConfigLoader_i, CommandLoader_i
from doot.control.locations import DootLocData
from doot.task.task import DootTask
from doot.task.group import TaskGroup
from doot.tasker import DootTasker
from doot.utils.check_dirs import CheckDir
from doot.utils.gen_toml import GenToml
from doot.utils.task_namer import task_namer

TASK_STRING = "task_"

##-- loader cli params
#### options related to dooter.py
# select dodo file containing tasks
opt_doot = {
    "section" : "task loader",
    "name"    : "dooter",
    "short"   : "f",
    "long"    : "file",
    "type"    : str,
    "default" : str(doot.default_dooter),
    "env_var" : "DOOT_FILE",
    "help"    : "load task from doot FILE [default: %(default)s]"
}

opt_break = {
    "section" : "task loader",
    "name"    : "break",
    "short"   : "b",
    "long"    : "break",
    "type"    : bool,
    "default" : False,
    "help"    : "Start a debugger before loading tasks, to set breakpoints"
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

##-- end loader cli params

class DootConfigLoader(ConfigLoader_i):

    def load(self) -> Tomler:
        self.config = doot.config.get_table()

        # load config files
        config_filenames = filter(pl.Path.exists, map(pl.Path.expanduser, map(pl.Path, config_filenames)))

        # add extra config
        match extra_config:
            case None:
                self.extra_config = None
            case dict():
                self.extra_config = tomler.Tomler(table=extra_config)
            case tomler.Tomler():
                self.extra_config = extra_config
        return self.config

    def load_plugins(self):
        """
        use entry_points(group="doot")
        add to the config tomler
        """
        pass
