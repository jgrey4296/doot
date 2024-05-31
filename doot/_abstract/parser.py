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

from abc import abstractmethod
from tomlguard import TomlGuard
from jgdv.structs.regex import RegexEqual

from doot._abstract.protocols import ParamStruct_p

class ArgParser_i:
    """
    A Single standard process point for turning the list of passed in args,
    into a dict, into a tomlguard,
    along the way it determines the cmds and tasks that have been chosne
    """

    @abstractmethod
    def parse(self, args:list[str], doot_arg_specs:list[ParamStruct_p], cmds:TomlGuard, tasks:TomlGuard) -> TomlGuard:
        pass
