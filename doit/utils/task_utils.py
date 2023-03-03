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

def dict_to_task(task_dict):
    """Create a task instance from dictionary.

    The dictionary has the same format as returned by task-generators
    from dodo files.

    @param task_dict (dict): task representation as a dict.
    @raise InvalidTask: If unexpected fields were passed in task_dict
    """
    # check required fields
    if 'actions' not in task_dict:
        raise InvalidTask("Task %s must contain 'actions' field. %s" %
                          (task_dict['name'], task_dict))

    # user friendly. dont go ahead with invalid input.
    task_attrs = list(task_dict.keys())
    valid_attrs = set(Task.valid_attr.keys())
    for key in task_attrs:
        if key not in valid_attrs:
            name = task_dict['name']
            raise InvalidTask(f"Task {name} contains invalid field: '{key}'")

    return Task(**task_dict)



def clean_targets(task, dryrun):
    """remove all targets from a task"""
    for target in sorted(task.targets, reverse=True):
        if os.path.isfile(target):
            print("%s - removing file '%s'" % (task.name, target))
            if not dryrun:
                os.remove(target)
        elif os.path.isdir(target):
            if os.listdir(target):
                msg = "%s - cannot remove (it is not empty) '%s'"
                print(msg % (task.name, target))
            else:
                msg = "%s - removing dir '%s'"
                print(msg % (task.name, target))
                if not dryrun:
                    os.rmdir(target)


# uptodate
