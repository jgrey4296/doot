#/usr/bin/env python3
"""
A Task which groups other tasks then yields them

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
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

    def __init__(self, name, *args):
        self.create_doit_tasks = self._build_task
        self.name              = name.replace(" ", "_")
        self.tasks             = list(args)

    def _build_task(self):
        for task in self.tasks:
            try:
                result = task
                match task:
                    case dict():
                        pass
                    case x if hasattr(x, "create_doit_tasks"):
                        result = task.create_doit_tasks()
                    case x if hasattr(x, "build") and callable(x.build):
                        result = task.build()
                    case x if callable(x):
                        result = task()

                if isinstance(result, list):
                    for x in result:
                        yield x
                elif result is not None:
                    yield result
            except DootDirAbsent:
                continue

        yield { "basename" : "_groups::" + self.name,
                "actions" : [],
                }


    def __iadd__(self, other):
        self.tasks.append(other)
        return self

    def add_tasks(self, *other):
        for x in other:
            self.tasks.append(other)
