
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

import doot
from doot._abstract.cmd import Command_i
from doot._abstract.parser import DootParamSpec
from collections import defaultdict


class ListCmd(Command_i):
    _name      = "list"
    _help      = []
    STATUS_MAP = {'ignore': 'I', 'up-to-date': 'U', 'run': 'R', 'error': 'E'}

    @property
    def param_specs(self) -> list:
        return [
            DootParamSpec(name="all", default=True),
            DootParamSpec(name="dependencies", default=False),
            DootParamSpec(name="target", type=str, default=""),

            ]

    def __call__(self, tasks:dict, plugins:dict):
        """List task generators"""
        logging.debug("Starting to List Taskers/Tasks")
        if doot.args.cmd.args.all:
            for key, tasker in tasks:
                logging.info("%s : %s", key, tasker)

        if doot.args.cmd.target != "":
            # TODO expand the tasks of specified tasker
            pass
