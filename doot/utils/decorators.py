#!/usr/bin/env python2
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

import inspect
import abc
import builtins
from typing import Type
import decorator
import doot
import doot.errors
from doot.enums import LocationMeta
from doot._abstract.structs import SpecStruct_p

FUNC_WRAPPED     : Final[str]                = "__wrapped__"
DOOT_ANNOTATIONS : Final[str]                = "__DOOT_ANNOTATIONS__"

RUN_DRY_SWITCH                               = doot.constants.decorations.RUN_DRY_SWITCH
RUN_DRY                                      = doot.constants.decorations.RUN_DRY
GEN_TASKS                                    = doot.constants.decorations.GEN_TASKS
IO_ACT                                       = doot.constants.decorations.IO_ACT
CONTROL_FLOW                                 = doot.constants.decorations.CONTROL_FLOW
EXTERNAL                                     = doot.constants.decorations.EXTERNAL
STATE_MOD                                    = doot.constants.decorations.STATE_MOD
ANNOUNCER                                    = doot.constants.decorations.ANNOUNCER

dry_run_active                               = doot.args.on_fail(False).cmd.args.dry_run()

class DootDecorator(abc.ABC):
    """ Base Class for decorators that annotate action callables
      set self._annotations:dict to add annotations to fn.__DOOT_ANNOTATIONS (:set)
      implement self._wrapper to add a wrapper around the fn.
      TODO: set self._idempotent=True to only add a wrapper once
      """

    def __init__(self):
        self._idempotent  = False
        self._annotations =  set()

    def __call__(self, fn):
        if bool(self._annotations):
            self.annotate(fn, self._annotations)

        if not hasattr(self, "_wrapper"):
            return fn

        if isinstance(fn, Type):
            return self.wrap_method(fn, fn.__call__, self._wrapper)

        decorated = decorator.decorate(fn, self._wrapper)
        return decorated

    @staticmethod
    def _strip_wrappers(fn:callable) -> callable:
        # if not hasattr(fn, FUNC_WRAPPED):
        #     return fn

        # return getattr(fn, FUNC_WRAPPED)
        return inspect.unwrap(fn)

    @staticmethod
    def has_annotations(fn, *keys) -> bool:
        base = DootDecorator._strip_wrappers(fn)
        if not hasattr(base, DOOT_ANNOTATIONS):
            return False

        annots = getattr(base, DOOT_ANNOTATIONS)
        return all(key in annots for key in keys)

    @staticmethod
    def annotate(fn:callable, annots:set) -> callable:
        base = DootDecorator._strip_wrappers(fn)
        if not hasattr(base, DOOT_ANNOTATIONS):
            setattr(base, DOOT_ANNOTATIONS, set())

        annotations = getattr(base, DOOT_ANNOTATIONS)
        for cls in getattr(fn, '__mro__', []):
            annotations.update(getattr(cls, DOOT_ANNOTATIONS, {}))

        annotations.update(annots)
        return fn

    @staticmethod
    def wrap_method(obj:Type, method:callable, wrapper:callable) -> Type:
        wrapped = decorator.decorate(method, wrapper)
        setattr(obj, method.__name__, wrapped)
        return obj

    @staticmethod
    def truncate_signature(fn):
        """
           actions are (self?, spec, state)
          with and extracted keys from the spec and state.
          This truncates the signature of the action to what is *called*, not what is *used*.

          TODO: could take a callable as the prototype to build the signature from
        """
        sig = inspect.signature(fn)
        min_index = len(sig.parameters) - len(getattr(fn, "_doot_keys"))
        newsig = sig.replace(parameters=list(sig.parameters.values())[:min_index])
        fn.__signature__ = newsig
        return fn

class DryRunSwitch(DootDecorator):
    """ Mark an action callable/class as to be skipped in dry runs """

    def __init__(self, *, override:bool=False):
        self._override = override
        self._annotations = {RUN_DRY_SWITCH}

    def _wrapper(self, fn, *args, **kwargs):
        if dry_run_active or self._override:
            return None
        return fn(*args, **kwargs)

class RunsDry(DootDecorator):
    """ mark an action that makes no changes to the system, on an honour system """

    def __init__(self):
        self._annotations = {RUN_DRY}

class GeneratesTasks(DootDecorator):
    """ Mark an action callable/class as a task generator """

    def __init__(self):
        self._annotations = {GEN_TASKS}

    def _wrapper(self, fn, *args, **kwargs):
        result = fn(*args, **kwargs)
        if isinstance(result, Generator):
            raise NotImplementedError("Actions can't return generators yet to generate tasks")
        if not isinstance(result, list):
            raise doot.errors.DootActionError("Action did not return a list of generated tasks")
        if any(not isinstance(x, SpecStruct_p) for x in result):
            raise doot.errors.DootActionError("Action did not return task specs")
        return result

class IOWriter(DootDecorator):
    """ mark an action callable/class as an io action,
      checks the path it'll write to isn't write protected
    """

    def __init__(self, *targets):
        super().__init__()
        self._annotations = {IO_ACT}
        self._targets = [x for x in targets or ["to"]]

    def _wrapper(self, fn, spec, state, *args, **kwargs):
        for x in [y for y in getattr(fn, '_doot_keys', []) if y in self._targets]:
            if doot.locs._is_write_protected(x.to_path(spec, state)):
                raise doot.errors.DootTaskError("A Target to an IOWriter action is marked as protected")

        return fn(spec, state, *args, **kwargs)

class ControlFlow(DootDecorator):
    """ mark an action callable/class as a control flow action
      implies it runs dry
      """
    pass

class External(DootDecorator):
    """ mark an action callable/class as calling an external program.
      implies rundryswitch
      """
    pass

class StateManipulator(DootDecorator):
    """ mark an action callable/class as a state modifier
      checks the DootKey `returns` are in the return dict
    """
    pass

class Announcer(DootDecorator):
    """ mark an action callable/class as reporting in a particular way
      implies run_dry, and skips on cli arg `silent`
      """
    pass
