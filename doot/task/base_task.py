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
import doot.constants
from doot._abstract import Task_i, Job_i, Action_p, PluginLoader_p
from doot.enums import TaskFlags
from doot.structs import TaskStub, TaskStubPart, DootActionSpec, DootCodeReference
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

    def __init__(self, spec, *, job=None, action_ctor=None, **kwargs):
        super().__init__(spec, job=job, **kwargs)
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
        if bool(list(filter(lambda x: x[0] == "task", doot.constants.DEFAULT_PLUGINS['task']))):
            stub.ctor = "task"
        else:
            stub.ctor                   = cls

        # Come first
        stub['active_when'].priority    = -90
        stub['required_for'].priority   = -90
        stub['depends_on'].priority     = -100

        stub['print_levels'].type       = f"Dict: {doot.constants.PRINT_LOCATIONS}"
        stub['print_levels'].default    = {"head":"INFO","build":"INFO","sleep":"INFO","action":"INFO", "execute":"INFO"}

        stub['priority'].default        = 10
        stub['queue_behaviour'].default = "default"
        stub['queue_behaviour'].comment = "default | auto | reactive"
        return stub

    def stub_instance(self, stub) -> TaskStub:
        """ extend the class toml stub with details from this instance """
        stub['name'].default      = self.fullname
        if bool(self.doc):
            stub['doc'].default   = self.doc[:]
        stub['flags'].default     = self.spec.flags

        return stub

    def prepare_actions(self):
        """ if the task/action spec requires particular action ctors, load them.
          if the action spec doesn't have a ctor, use the task's action_ctor
        """
        logging.info("Preparing Actions: %s", self.name)
        for action_spec in self.spec.actions:
            assert(isinstance(action_spec, DootActionSpec)), action_spec
            if action_spec.fun is not None:
                continue
            if action_spec.do  is not None:
                action_ref = self.import_callable(action_spec.do)
                action_spec.set_function(action_ref)
                continue

            assert(action_spec.do is None), action_spec
            action_spec.set_function(self.action_ctor)
