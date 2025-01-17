#!/usr/bin/env python3
"""
Action Decorators for metadata.

"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.decorators import MetaDecorator

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

RUN_DRY_SWITCH                               = doot.constants.decorations.RUN_DRY_SWITCH
RUN_DRY                                      = doot.constants.decorations.RUN_DRY
GEN_TASKS                                    = doot.constants.decorations.GEN_TASKS
IO_ACT                                       = doot.constants.decorations.IO_ACT
CONTROL_FLOW                                 = doot.constants.decorations.CONTROL_FLOW
EXTERNAL                                     = doot.constants.decorations.EXTERNAL
STATE_MOD                                    = doot.constants.decorations.STATE_MOD
ANNOUNCER                                    = doot.constants.decorations.ANNOUNCER

dry_run_active                               = doot.args.on_fail(False).cmd.args.dry_run()

class DryRunSwitch(MetaDecorator):
    """ Mark an action callable/class as to be skipped in dry runs """

    def __init__(self, *, override:bool=False):
        super().__init__("dry_run", mark="_dry_run_mark")
        self._override = override or dry_run_active

    def _wrap_method(self, fn):
        override_active = self._override or dry_run_active

        def _can_disable(*args, **kwargs):
            if override_active:
                return None
            return fn(*args, **kwargs)

        return _can_disable

    def _wrap_fn(self, fn):
        return self._wrap_method(fn)

class GeneratesTasks(MetaDecorator):
    """ Mark an action callable/class as a task generator """

    def __init__(self):
        super().__init__(GEN_TASKS, mark="_gen_data_mark")

    def _wrap_fn(self, fn):

        def _gen_task_wrapper(*args, **kwargs):
            match fn(*args, **kwargs):
                case [*xs] if any(not isinstance(x, SpecStruct_p) for x in xs):
                    raise doot.errors.ActionCallError("Action did not return task specs")
                case list() as res:
                    return res
                case _:
                    raise doot.errors.ActionCallError("Action did not return a list of generated tasks")

        return _gen_task_wrapper

class IOWriter(MetaDecorator):
    """ mark an action callable/class as an io action,
      checks the path it'll write to isn't write protected
    """

    def __init__(self):
        super().__init__(IO_ACT, mark="_io_mark")
        self._targets = [x for x in targets or ["to"]]

    def _wrap_fn(self, fn):

        def _io_writer_wrapper(*args, **kargs):
            result = fn(*args, **kwargs)
            raise NotImplementedError()

        return _io_writer_wrapper

class ControlFlow(MetaDecorator):
    """ mark an action callable/class as a control flow action
      implies it runs dry
      """

    def __init__(self):
        super().__init__(CONTROL_FLOW, mark="_control_flow_mark")

class External(MetaDecorator):
    """ mark an action callable/class as calling an external program.
      implies rundryswitch
      """

    def __init__(self):
        super().__init__(EXTERNAL, mark="_external_mark")

class StateManipulator(MetaDecorator):
    """ mark an action callable/class as a state modifier
      checks the DootKey `returns` are in the return dict
    """

    def __init__(self):
        super().__init__(STATE_MOD, mark="_state_mod_mark")

class Announcer(MetaDecorator):
    """ mark an action callable/class as reporting in a particular way
      implies run_dry, and skips on cli arg `silent`
      """

    def __init__(self):
        super().__init__(ANNOUNCER, mark="_announcer_mark")
