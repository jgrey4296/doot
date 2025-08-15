#!/usr/bin/env python3
"""

"""
# ruff: noqa:

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import re
import time
import types
import collections
import contextlib
import hashlib
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref
import atexit # for @atexit.register
import faulthandler
# ##-- end stdlib imports
from importlib.metadata import EntryPoint
from jgdv._abstract.protocols.general import SpecStruct_p
import doot
from doot.cmds._interface import Command_p

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload
if TYPE_CHECKING:
    import pathlib as pl
    from jgdv import Maybe
    from jgdv.structs.chainguard import ChainGuard
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Types
type Loaders_p             = CommandLoader_p | PluginLoader_p | TaskLoader_p
type PluginLoader_p        = Loader_p[EntryPoint]
type CommandLoader_p       = Loader_p[Command_p]
type TaskLoader_p          = Loader_p[SpecStruct_p]
# Body:

@runtime_checkable
class Loader_p[T](Protocol):

    def setup(self, data:ChainGuard) -> Self: ...

    def load(self) -> ChainGuard: ...
