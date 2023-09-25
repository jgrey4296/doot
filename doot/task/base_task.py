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

import importlib
import doot
import doot.errors
import tomler
from doot._abstract import Task_i, Tasker_i, Action_p, PluginLoader_p
from doot.enums import TaskFlags, StructuredNameEnum
from doot.structs import DootStructuredName, TaskStub, TaskStubPart
from doot.actions.base_action import DootBaseAction
from doot.errors import DootTaskLoadError

from doot.mixins.importer import ImporterMixin

ACTION_CTORS = {x.name : x.load() for x in PluginLoader_p.loaded.action}

@doot.check_protocol
class DootTask(Task_i, ImporterMixin):
    """
      The simplest task, which can import action classes.
      eg:
      actions = [ {ctor = "doot.actions.shell_action:DootShellAction", args = ["echo", "this is a test"] } ]
    """
    action_ctor    = DootBaseAction
    _default_flags = TaskFlags.TASK
    _help          = ["The Simplest Task"]

    def __init__(self, spec, *, tasker=None, **kwargs):
        super().__init__(spec, tasker=tasker, **kwargs)
        self.prepare_actions()

    @property
    def actions(self):
        """lazy creation of action instances,
          `prepare_actions` has already ensured all ctors can be found
        """
        for action_spec in self.spec.actions:
            match action_spec:
                case list() as args:
                    yield self.action_ctor(tomler.Tomler({"args": args}))
                case { "ctor" : str() as ctor_name, "args" : list() }:
                    ctor = ACTION_CTORS[ctor_name]
                    yield ctor(tomler.Tomler(action_spec))
                case { "fun"  : str() as fun_name,  "args" : list() }:
                    fun = ACTION_CTORS[fun_name]
                    yield ftz.partial(fun, tomler.Tomler(action_spec))
                case { "fun"  : str() as fun_name,  "args" : list() }:
                    fun = ACTION_CTORS(fun_name)
                    yield ftz.partial(fun, tomlerTomler(action_spec))
                case _:
                    raise DootTaskError("Bad Action Spec", self.name, action)

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

    def prepare_actions(self):
        """ if the task spec requires particular action ctors, load them """
        logging.info("Preparing Actions: %s", self.name)
        for action_spec in self.spec.actions:
            match action_spec:
                case list():
                    pass
                case { "ctor" : str() as ctor_name, "args" : list() } if ctor_name not in ACTION_CTORS:
                    ctor = self.import_class(ctor_name)
                    ACTION_CTORS[ctor_name] = ctor
                case { "fun"  : str() as fun_name,  "args" : list()} if fun_name not in ACTION_CTORS:
                    fun = self.import_class(fun_name)
                    ACTION_CTORS[fun_name] = fun
                case { "ctor" : str() } | { "fun"  : str() }:
                    pass
                case _:
                    raise DootTaskLoadError("Bad Action Spec", self.name, action_spec)
