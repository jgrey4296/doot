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


class Interactive(CmdAction):
    """Action to handle Interactive shell process:

       * the output is never captured
    """
    def execute(self, out=None, err=None):
        action = self.expand_action()
        process = subprocess.Popen(
            action, shell=self.shell, stdout=out, stderr=err, **self.pkwargs)
        process.wait()
        if process.returncode != 0:
            return exceptions.TaskFailed(
                "Interactive command failed: '%s' returned %s" %
                (action, process.returncode))
