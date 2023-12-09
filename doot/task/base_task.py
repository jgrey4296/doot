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

printer = logmod.getLogger("doot._printer")

import doot
import doot.errors
import tomlguard
from doot._abstract import Task_i, Tasker_i, Action_p, PluginLoader_p
from doot.enums import TaskFlags, StructuredNameEnum
from doot.structs import DootStructuredName, TaskStub, TaskStubPart, DootActionSpec
from doot.actions.base_action import DootBaseAction
from doot.errors import DootTaskLoadError, DootTaskError

from doot.mixins.importer import ImporterMixin

@doot.check_protocol
class DootTask(Task_i, ImporterMixin):
    """
      The simplest task, which can import action classes.
      eg:
      actions = [ {do = "doot.actions.shell_action:DootShellAction", args = ["echo", "this is a test"] } ]
    """
    action_ctor    = DootBaseAction
    _default_flags = TaskFlags.TASK
    _help          = ["The Simplest Task"]

    def __init__(self, spec, *, tasker=None, action_ctor=None, **kwargs):
        super().__init__(spec, tasker=tasker, **kwargs)
        if action_ctor:
            self.action_ctor = action_ctor
        self.prepare_actions()

    @property
    def actions(self):
        """lazy creation of action instances,
          `prepare_actions` has already ensured all ctors can be found
        """
        yield from iter(self.spec.actions)

    @property
    def is_stale(self):
        return False

    @classmethod
    def stub_class(cls, stub) -> TaskStub:
        """ Create a basic toml stub for this task"""
        stub.ctor               = cls
        stub['version'].default = cls._version
        stub['doc'].default     = [f"\"{x}\"" for x in cls.class_help().split("\n") if bool(x)]
        stub['flags'].default   = cls._default_flags
        return stub

    def stub_instance(self, stub) -> TaskStub:
        """ extend the class toml stub with details from this instance """
        stub['name'].default      = self.fullname
        if bool(self.doc):
            stub['doc'].default   = [f"\"{x}\"" for x in self.doc]
        stub['flags'].default     = self.spec.flags

        return stub

    def prepare_actions(self):
        """ if the task/action spec requires particular action ctors, load them.
          if the action spec doesn't have a ctor, use the task's action_ctor
        """
        logging.info("Preparing Actions: %s", self.name)
        for action_spec in self.spec.actions:
            assert(isinstance(action_spec, DootActionSpec))
            if action_spec.fun is not None:
                continue
            if action_spec.do  is not None:
                action_id = action_spec.do
                action_spec.set_function(self.import_callable(action_id))
                continue

            assert(action_spec.do is None), action_spec
            action_spec.set_function(self.action_ctor)
