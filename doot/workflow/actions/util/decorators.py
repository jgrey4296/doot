#!/usr/bin/env python3
"""
Action Decorators for metadata.

"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.decorators import MetaDec, IdempotentDec

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors

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

##--|
from jgdv._abstract.protocols import SpecStruct_p
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

RUN_DRY_SWITCH                               = doot.constants.decorations.RUN_DRY_SWITCH
GEN_TASKS                                    = doot.constants.decorations.GEN_TASKS
IO_ACT                                       = doot.constants.decorations.IO_ACT
CONTROL_FLOW                                 = doot.constants.decorations.CONTROL_FLOW
EXTERNAL                                     = doot.constants.decorations.EXTERNAL
STATE_MOD                                    = doot.constants.decorations.STATE_MOD
ANNOUNCER                                    = doot.constants.decorations.ANNOUNCER

dry_run_active                               = doot.args.on_fail(False).cmd.args.dry_run()
##--|

class _BaseMetaAction(IdempotentDec):

    def _wrap_fn_h(self, fn):
        return self._wrap_method_h(fn)

    def _wrap_class_h(self, cls):
        cls.__call__ = self._wrap_method_h(cls.__call__)
        return cls

class DryRunSwitch(_BaseMetaAction):
    """ Mark an action callable/class as to be skipped in dry runs """

    def __init__(self, *, override:bool=False):
        super().__init__("dry_run", mark="_dry_run_mark")
        self._override = override or dry_run_active

    def _wrap_method_h(self, fn):
        override_active = self._override or dry_run_active

        def _can_disable(*args, **kwargs):
            if override_active:
                return None
            return fn(*args, **kwargs)

        return _can_disable

class GeneratesTasks(_BaseMetaAction):
    """ Mark an action callable/class as a task generator """

    def __init__(self):
        super().__init__(GEN_TASKS, mark="_gen_data_mark")

    def _wrap_fn_h(self, fn):

        def _gen_task_wrapper(*args, **kwargs):
            match fn(*args, **kwargs):
                case [*xs] if any(not isinstance(x, SpecStruct_p) for x in xs):
                    raise doot.errors.ActionCallError("Action did not return task specs")
                case list() as res:
                    return res
                case _:
                    raise doot.errors.ActionCallError("Action did not return a list of generated tasks")

        return _gen_task_wrapper

class IOWriter(_BaseMetaAction):
    """ mark an action callable/class as an io action,
      checks the path it'll write to isn't write protected
    """

    def __init__(self, *, targets=None):
        super().__init__(IO_ACT, mark="_io_mark")
        self._targets = targets or ["to"]

    def _wrap_fn_h(self, fn):

        def _io_writer_wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            raise NotImplementedError()

        return _io_writer_wrapper

class ControlFlow(_BaseMetaAction):
    """ mark an action callable/class as a control flow action
      implies it runs dry
      """

    def __init__(self):
        super().__init__(CONTROL_FLOW, mark="_control_flow_mark")

class External(_BaseMetaAction):
    """ mark an action callable/class as calling an external program.
      implies rundryswitch
      """

    def __init__(self):
        super().__init__(EXTERNAL, mark="_external_mark")

class StateManipulator(_BaseMetaAction):
    """ mark an action callable/class as a state modifier
      checks the DootKey `returns` are in the return dict
    """

    def __init__(self):
        super().__init__(STATE_MOD, mark="_state_mod_mark")

class Announcer(_BaseMetaAction):
    """ mark an action callable/class as reporting in a particular way
      implies run_dry, and skips on cli arg `silent`
      """

    def __init__(self):
        super().__init__(ANNOUNCER, mark="_announcer_mark")
