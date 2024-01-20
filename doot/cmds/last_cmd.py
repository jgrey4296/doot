#!/usr/bin/env python3
"""
Print a summary of the last run

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

printer = logmod.getLogger("doot._printer")

from collections import defaultdict
from tomlguard import TomlGuard
import doot
import doot.errors
from doot._abstract import Command_i
from doot.structs import DootParamSpec


INDENT : Final[str] = " "*8

@doot.check_protocol
class LastCmd(Command_i):
    _name      = "last"
    _help      = ["Summarise the last run"]
    STATUS_MAP = {'ignore': 'I', 'up-to-date': 'U', 'run': 'R', 'error': 'E'}

    @property
    def param_specs(self) -> list[DootParamSpec]:
        return super().param_specs + [
            self.make_param(name="all",                                          default=True,                   desc="List all loaded tasks, by group"),
            self.make_param(name="dependencies",                                 default=False,                  desc="List task dependencies",                 prefix="--"),
            self.make_param(name="dag",       _short="D",                        default=False,                  desc="Output a DOT compatible graph of tasks", prefix="--"),
            self.make_param(name="groups",                   type=bool,          default=False,                  desc="List just the groups tasks fall into",   prefix="--"),
            self.make_param(name="by-source",                                    default=False,                  desc="List all loaded tasks, by source file",  prefix="--"),
            self.make_param(name="locations", _short="l",    type=bool,          default=False,                  desc="List all Loaded Locations"),
            self.make_param(name="internal",  _short="i",    type=bool,          default=False,                  desc="Include internal tasks (ie: prefixed with an underscore)"),
            self.make_param(name="pattern",                  type=str,           default="", positional=True,    desc="List tasks with a basic string pattern in the name"),
            ]

    def __call__(self, tasks:TomlGuard, plugins:TomlGuard):
        """List task generators"""
        logging.debug("Starting to List Jobs/Tasks")

        raise NotImplementedError("TODO")
