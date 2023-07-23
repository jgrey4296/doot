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

from tomler import Tomler
from doot._abstract.control import TaskOrdering_i
from doot._abstract.parser import ParamSpecMaker_mixin

class Tasker_i(TaskOrdering_i, ParamSpecMaker_mixin):
    """
    builds task descriptions
    """
    task_type : Task_i
    _version  : str = "0.1"
    _help     : list[str] = []

    @classmethod
    def _make_task(cls, *arg, **kwargs):
        return cls.task_type(*arg, **kwargs)

    def __init__(self, spec:dict|Tomler, locs:DootLocData=None):
        assert(locs is not None or locs is False), locs

        match spec:
            case None:
                raise TypeError("Task Spec cannot be None")
            case dict():
                self.spec = Tomler(spec)
            case Tomler():
                self.spec = spec
            case _:
                raise TypeError("Unrecognized Task Spec Type")

        self.basename = self.spec.name
        self.subgroups = self.spec.on_fail([], list).subgroups()
        # TODO: wrap with importlib:
        self.task_type = self.spec.on_fail(DootTask).task_type()

        self.locs             = locs
        self.args             = {}
        self._setup_name      = None
        self.has_active_setup = False
        self.output           = output

    @property
    def setup_name(self):
        if self._setup_name is not None:
            return self._setup_name

        self._setup_name = task_namer(self.basename, "setup", private=True)
        return self._setup_name

    @property
    def fullname(self):
        return task_namer(self.basename, *self.subgroups)

    @property
    def doc(self):
        try:
            split_doc = [x for x in self.__class__.__doc__.split("\n") if bool(x)]
            return ":: " + split_doc[0].strip() if bool(split_doc) else ""
        except AttributeError:
            return ":: "


    @classmethod
    @property
    def help(cls) -> str:
        """ Tasker *class* help. """
        help_lines = [f"Tasker : {cls.__qualname__} v{cls._version}", ""]
        help_lines += cls._help

        params = cls.param_specs
        if bool([x for x in params if not x.invisible]):
            help_lines += ["", "Params:"]
            help_lines += [str(x) for x in cls.param_specs if not x.invisible]

        return "\n".join(help_lines)
    @classmethod
    @property
    def param_specs(cls) -> list[parser.DootParamSpec]:
        return [
           cls.make_param(name="help", default=False, invisible=True),
           cls.make_param(name="debug", default=False, invisible=True)
           ]

    def default_task(self) -> dict:
        raise NotImplementedError()

    def default_meta(self) -> dict:
        raise NotImplementedError()

    def is_current(self, task:DootTask):
        raise NotImplementedError()

    def clean(self, task:DootTask):
        raise NotImplementedError()

    def setup_detail(self, task:dict) -> None|dict:
        raise NotImplementedError()

    def task_detail(self, task:dict) -> dict:
        raise NotImplementedError()

    def build(self, **kwargs) -> GeneratorType:
        raise NotImplementedError()

    def stub_spec(self) -> DootTaskStub:
        """
        Return a list of StubSpec's
        to describe how this tasker is specified in toml
        """
        raise NotImplementedError()

    def log(self, msg, level=logmod.DEBUG, prefix=None):
        """
        utility method to log a message, useful as tasks are running
        """
        prefix = prefix or ""
        lines  = []
        match msg:
            case str():
                lines.append(msg)
            case types.LambdaType():
                lines.append(msg())
            case [types.LambdaType()]:
                lines += msg[0]()
            case list():
                lines += msg

        for line in lines:
            logging.log(level, prefix + str(line))
