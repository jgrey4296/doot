#!/usr/bin/env python3
"""
Extension to Doit's Task and Actions,
To allow:
1) returning an Action from an Action and using it
2) only calling a CmdAction's python callable once
3) putting any extraneous kwargs in a task dict into the `meta` dict automatically
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

printer = logmod.getLogger("doot._printer")

import doot
import doot.errors
import tomler
from doot._abstract import Task_i, Tasker_i, Action_p
from doot.enums import TaskFlags
from doot.structs import DootStructuredName, TaskStub, TaskStubPart
from doot.actions.base_action import DootBaseAction

@doot.check_protocol
class DootTask(Task_i):
    """
      The simplest task
    """
    action_ctor    = DootBaseAction
    _default_flags = TaskFlags.TASKER
    _help          = ["The Simplest Task"]

    @property
    def actions(self):
        """lazy creation of action instances"""
        action_ctor = self.spec.extra.on_fail(DootTask.action_ctor).action_ctor()
        for action in self.spec.actions:
            yield action_ctor(action)

    @property
    def is_stale(self):
        return False

    @classmethod
    def stub_class(cls) -> TaskStub:
        """ Create a basic toml stub for this task"""
        stub = TaskStub(ctor=cls.__class__)
        stub['doc'].default   = [f"\"{x}\"" for x in cls.class_help().split("\n") if bool(x)]
        stub['flags'].default = cls._default_flags
        return stub

    def stub_instance(self) -> TaskStub:
        """ extend the class toml stub with  """
        stub                      = self.__class__.stub_class()
        stub['name'].default      = self.fullname
        if bool(self.doc):
            stub['doc'].default   = [f"\"{x}\"" for x in self.doc]
        stub['flags'].default     = self.spec.flags

        return stub
