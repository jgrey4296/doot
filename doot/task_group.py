#/usr/bin/env python3
"""
A Task which groups other tasks then yields them

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
import types
import re
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

from doot.errors import DootDirAbsent

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

clean_re = re.compile("\s+")

class TaskGroup:
    """ A Group of task specs, none of which require params
    Can contain: dicts, objects with a `_build_task` method,
    objects with `create_doit_tasks`, and callables
    """

    def __init__(self, name, *args, as_creator=False):
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
        # this can add taskers to the namespace,
        # but doesn't help for dicts
        return {f"doot_{self.name}_{id(x)}": x for x in self.tasks}


    def add_tasks(self, *other):
        for x in other:
            self.tasks.append(other)
