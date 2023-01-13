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

    def __init__(self, name, *args, as_creator=False):
        self.name       = name.replace(" ", "_")
        self.tasks      = list(args)
        self.as_creator = as_creator
        if as_creator:
            self.create_doit_tasks = lambda *a, **kw: self._build_task(*a, **kw)
            self.create_doit_tasks.__dict__['basename'] = name

    def to_dict(self):
        return {f"__doot_{self.name}_{id(x)}": x for x in self.tasks}

    def __iadd__(self, other):
        self.tasks.append(other)
        return self

    def add_tasks(self, *other):
        for x in other:
            self.tasks.append(other)

    def _build_task(self):
        yield {
            "basename" : self.name,
            "name"     : None,
            "uptodate" : [False],
            "actions"  : [],
        }

        for task in self.tasks:
            yield task._build_task()

