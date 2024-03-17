#!/usr/bin/env python3
"""


See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

import doot
import doot.errors
from doot.structs import DootKey

class DootActionDecorator:
    """ Base Class for decorators that annotate action callables """

    def __init__(self, funcOrCls:Callable):
        ftz.update_wrapper(self, funcOrCls)
        self._func = func

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

class dry_runnable(DootActionDecorator):
    """ Mark an action callable/class as to be skipped in dry runs """
    pass


class generates_tasks(DootActionDecorator):
    """ Mark an action callable/class as a task generator """
    pass

class io_action(DootActionDecorator):
    """ mark an action callable/class as an io action """
    pass

class control_flow(DootActionDecorator):
    """ mark an action callable/class as a control flow action """
    pass

class external(DootActionDecorator):
    """ mark an action callable/class as calling an external program """
    pass

class state(DootActionDecorator):
    """ mark an action callable/class as a state modifier """
    pass

class announce(DootActionDecorator):
    """ mark an action callable/class as reporting in a particular way """
    pass
