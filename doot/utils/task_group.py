#/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

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

class TaskGroup:
    """ A Group of task specs, none of which require params
    Can contain: dicts, objects with a `build` method,
    objects with `create_doit_tasks`, and callables
    """


    def __init__(self, name, *args):
        self.create_doit_tasks = self.build
        self.name = name
        self.tasks = args

    def build(self):
        for task in self.tasks:
            if isinstance(task, dict):
                yield task
            elif hasattr(task, "build"):
                yield task.build()
            elif hasattr(task, "create_doit_tasks"):
                yield task.create_doit_tasks()
            elif callable(task):
                yield task()
