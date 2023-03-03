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


class PythonInteractiveAction(PythonAction):
    """Action to handle Interactive python:

       * the output is never captured
       * it is successful unless a exception is raised
    """
    def execute(self, out=None, err=None):
        kwargs = self._prepare_kwargs()
        try:
            returned_value = self.py_callable(*self.args, **kwargs)
        except Exception as exception:
            return exceptions.TaskError("PythonAction Error", exception)
        if isinstance(returned_value, str):
            self.result = returned_value
        elif isinstance(returned_value, dict):
            self.values = returned_value
            self.result = returned_value
