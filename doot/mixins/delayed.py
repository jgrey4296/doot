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

import sys

class DelayedMixin:
    """
    Delays Subtask generation until the main task is executed

    """
    delay_pattern = "_{}::delayed"

    def _build(self, **kwargs):
        try:
            self.args.update(kwargs)
            setup_task = self._build_setup()
            task       = self._build_task()
            task.task_dep.append(self.delay_pattern.format(self.base))

            if task is None:
                return None
            yield task

            if setup_task is not None:
                yield setup_task

        except Exception as err:
            logging.error("ERROR: Task Creation Failure: ", err)
            logging.error("ERROR: Task was: ", self.base)
            sys.exit(1)


    def _build_delayed(self, **kwargs):
        logging.debug("Delayed Tasks now building")
        yield from self._build_subs()
