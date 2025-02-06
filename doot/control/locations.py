#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field, replace
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    Generator, cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref
import functools as ftz

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

import os
import re

from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.locator.errors import DirAbsent, LocationExpansionError, LocationError
from jgdv.structs.locator import JGDVLocator, Location
from jgdv.structs.dkey import MultiDKey, NonDKey, SingleDKey, DKey, DKeyFormatter
from jgdv.mixins.path_manip import PathManip_m

import doot
from doot.structs import TaskArtifact

KEY_PAT                    = doot.constants.patterns.KEY_PATTERN
MAX_EXPANSIONS             = doot.constants.patterns.MAX_KEY_EXPANSIONS

DootLocator                = JGDVLocator
DootDirAbsent              = DirAbsent
DootLocationExpansionError = LocationExpansionError
DootLocationError          = LocationError
