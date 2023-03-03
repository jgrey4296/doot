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

class ModuleTaskLoader(NamespaceTaskLoader):
    """load tasks from a module/dictionary containing task generators
    Usage: `ModuleTaskLoader(my_module)` or `ModuleTaskLoader(globals())`
    """
    def __init__(self, mod_dict):
        super().__init__()
        if inspect.ismodule(mod_dict):
            self.namespace = dict(inspect.getmembers(mod_dict))
        else:
            self.namespace = mod_dict
