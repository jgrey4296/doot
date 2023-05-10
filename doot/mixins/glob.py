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

from time import sleep

class DirGlobMixin:
    """
    Globs for directories instead of files.
    Generates a subtask for each found directory

    Recursive: all directories from roots down
    Non-Recursive: immediate subdirectories roots
    Always provides the root directories
    """

    def glob_files(self, target, rec=None, fn=None, exts=None):
        if fn is None:
            fn = lambda x: True
        return super().glob_target(target, rec=rec, fn=fn, exts=exts)

    def glob_target(self, target, rec=None, fn=None, exts=None):
        results = []
        filter_fn = fn or self.filter
        if not target.exists():
            return []
        elif not (rec or self.rec):
            if filter_fn(target) not in [False, GlobControl.reject, GlobControl.discard]:
                results.append(target)
            results += [x for x in target.iterdir() if x.is_dir() and filter_fn(x) not in [False, GlobControl.reject, GlobControl.discard]]
            return results

        assert(rec or self.rec)
        queue = [target]
        while bool(queue):
            current = queue.pop()
            if not current.exists():
                continue
            if current.name in glob_ignores:
                continue
            if current.is_file():
                continue
            match filter_fn(current):
                case GlobControl.keep:
                    results.append(current)
                case GlobControl.discard:
                    queue += [x for x in current.iterdir() if x.is_dir()]
                case True | GlobControl.accept:
                    results.append(current)
                    queue += [x for x in current.iterdir() if x.is_dir()]
                case None | False | GlobControl.reject:
                    continue
                case _ as x:
                    raise TypeException("Unexpected glob filter value", x)

        return results
