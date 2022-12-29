#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations
from doit.tools import PythonInteractiveAction

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

def task_pyrepl():
    return {
        "basename" : "repl:py",
        "actions"  : [ PythonInteractiveAction(lambda: breakpoint()) ],
    }

def task_prolog_repl():
    return {
        "basename" : "repl::pl",
        "actions"  : [ Interactive(["swipl"], shell=False)],
    }
