#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types

# ##-- end stdlib imports

from jgdv import Proto

# ##-- 1st party imports
import doot
from doot.task.core.job import DootJob

# ##-- end 1st party imports

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
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from doot.structs import TaskSpec
##--|
from doot._abstract import Job_i
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@Proto(Job_i)
class GroupJob(DootJob):
    """ A Group of task specs, none of which require params """

    def __init__(self, spec:TaskSpec):
        super().__init__(spec)

    def __str__(self):
        return f"group:{self.name}({len(self)})"

    def __len__(self):
        return len(self.tasks)

    def __iadd__(self, other):
        self.tasks.append(other)
        return self

    def to_dict(self):
        # this can add jobs to the namespace,
        # but doesn't help for dicts
        return {f"doot_{self.name}_{id(x)}": x for x in self.tasks}

    def add_tasks(self, *other):
        for x in other:
            self.tasks.append(other)

@Proto(Job_i)
class WatchJob(DootJob):
    """
    Job that watches for conditions, *then*
    generates tasks.
    eg: a file watcher
    """
    pass
