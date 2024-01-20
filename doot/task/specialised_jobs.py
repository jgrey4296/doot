#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

# import abc
# import datetime
# import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
# from uuid import UUID, uuid1
# from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import doot
from doot.task.base_job import DootJob


@doot.check_protocol
class GroupJob(DootJob):
    """ A Group of task specs, none of which require params """

    def __init__(self, spec:DootTaskSpec):
        super().__init__(spec)
        self.name       = name.replace(" ", "_")
        self.tasks      = list(args)
        self.as_creator = as_creator

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

@doot.check_protocol
class WatchJob(DootJob):
    """
    Job that watches for conditions, *then*
    generates tasks.
    eg: a file watcher
    """
    pass
