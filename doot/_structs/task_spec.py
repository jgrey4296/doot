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
from dataclasses import InitVar, dataclass, field, _MISSING_TYPE
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

import importlib
from importlib.metadata import EntryPoint
from tomlguard import TomlGuard
import doot.errors
import doot.constants as consts
from doot.enums import TaskFlags, ReportEnum
from doot._structs.sname import DootTaskName, DootCodeReference
from doot._structs.action_spec import DootActionSpec
from doot._structs.artifact import DootTaskArtifact

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]

def _build_name(data) -> DootTaskName:
    match data:
        case {"group": group, "name": str() as name}:
            return DootTaskName(data['group'], data['name'])
        case {"name": str() as name}:
            return DootTaskName.from_str(name)
        case {"name": DootTaskName() as name}:
            return name
        case _:
            return DootTaskName(None, None)

def _separate_into_core_and_extra(data) -> tuple[dict, dict]:
    core_keys   = list(DootTaskSpec.__dataclass_fields__.keys())
    core_data, extra_data = dict(), dict()
    # Integrate extras, normalize keys
    for key, val in data.items():
        if "-" in key:
            key = key.replace("-","_")
        match key:
            case "extra":
                extra_data.update(dict(val))
            case "print_levels":
                core_data["print_levels"] = TomlGuard(val)
            case "active_when":
                processed = _prepare_deps(val)
                core_data["active_when"] = processed
            case "required_for":
                processed = _prepare_deps(val)
                core_data["required_for"] = processed
            case "depends_on":
                processed = _prepare_deps(val)
                core_data["depends_on"] = processed
            case x if x in core_keys:
                core_data[x] = val
            case x if x not in ["name", "group"]:
                extra_data[key] = val

    return core_data, extra_data

def _valid_flag(x):
    match x:
        case str() if x in TaskFlagNames:
            return True
        case TaskFlags():
            return True
        case _:
            return False

def _prepare_deps(deps:None|list[str], source=None) -> list[DootTaskArtifact|DootTaskName]:
    """
      Prepares dependencies, converting from strings to Artifacts (ie:files), or Task Names
      # TODO handle callables?
    """
    if deps is None:
        return []

    results = []
    for x in deps:
        match x:
            case { "task": taskname }:
                results.append(DootTaskName.from_str(taskname, args=x))
            case str() if x.startswith(consts.FILE_DEP_PREFIX):
                results.append(DootTaskArtifact(pl.Path(x.removeprefix(consts.FILE_DEP_PREFIX))))
            case str() if consts.TASK_SEP in x:
                results.append(DootTaskName.from_str(x))
            case DootTaskName() | DootTaskArtifact():
                results.append(x)
            case _:
                raise doot.errors.DootInvalidConfig(f"Unrecognised task pre/post dependency form. (Remember: files are prefixed with `{consts.FILE_DEP_PREFIX}`, tasks are in the form group::name)", x, source)

    return results

def _prepare_ctor(ctor, mixins):
    match ctor:
        case None:
            return DootCodeReference.from_str(doot.constants.DEFAULT_PLUGINS['task'][0][1]).add_mixins(*mixins)
        case EntryPoint():
            loaded = ctor.load()
            return DootCodeReference.from_type(loaded).add_mixins(*mixins)
        case DootTaskName() if bool(mixins):
            raise TypeError("Task name ctor can't take mixins")
        case DootTaskName():
            return ctor
        case DootCodeReference() if not bool(ctor._mixins):
            return ctor.add_mixins(*mixins)
        case DootCodeReference():
            return ctor
        case type():
            return DootCodeReference.from_type(ctor).add_mixins(*mixins)
        case str():
            return DootCodeReference.from_str(ctor).add_mixins(*mixins)
        case _:
            return DootCodeReference.from_type(ctor).add_mixins(*mixins)

@dataclass
class DootTaskSpec:
    """ The information needed to describe a generic task.
    Optional things are shoved into 'extra', so things can use .on_fail on the tomlguard

    the cli parser can understand cli=[{}] specs
    actions                      : list[ [args] | {do="", args=[], **kwargs} ]

    """
    name                         : DootTaskName                                                 = field()
    doc                          : list[str]                                                    = field(default_factory=list)
    source                       : DootTaskName|str|None                                        = field(default=None)
    actions                      : list[Any]                                                    = field(default_factory=list)

    active_when                  : list[DootTaskArtifact|callable]                              = field(default_factory=list)
    required_for                 : list[DootTaskName|DootTaskArtifact]                          = field(default_factory=list)
    depends_on                   : list[DootTaskName|DootTaskArtifact]                          = field(default_factory=list)
    priority                     : int                                                          = field(default=10)
    ctor                         : DootTaskName|DootCodeReference                               = field(default=None)
    # Any additional information:
    version                      : str                                             = field(default="0.1")
    print_levels                 : TomlGuard                                       = field(default_factory=TomlGuard)
    flags                        : TaskFlags                                       = field(default=TaskFlags.TASK)

    extra                        : TomlGuard                                       = field(default_factory=TomlGuard)

    inject                       : list[str]                                       = field(default_factory=list) # For jobs
    queue_behaviour              : str                                             = field(default="default")

    @staticmethod
    def from_dict(data:TomlGuard|dict):
        """ builds a task spec from a raw dict
          able to handle a name:str = "group::task" form,
          able to convert TaskFlag str's into an or'd enum value
          """
        core_data, extra_data = _separate_into_core_and_extra(data)

        core_data['name'] = _build_name(data)

        # Check flags are valid
        if any(flag for x in data.get('flags', []) if (flag:=x) and not _valid_flag(flag)):
            logging.warning("Unknown Task Flag used (%s), check the spec for %s in %s", flag, core_data['name'], data.get('source', ''))

        filtered = filter(lambda x: x in TaskFlagNames, core_data.get('flags', ["TASK"]))
        core_data['flags'] = ftz.reduce(lambda x,y: x|y, map(lambda x: TaskFlags[x],  filtered), TaskFlags.TASK)

        # Prepare constructor
        mixins = extra_data.get("mixins", [])
        core_data['ctor'] = _prepare_ctor(data.get("ctor",None), mixins)

        # prep actions
        core_data['actions'] = [DootActionSpec.from_data(x) for x in core_data.get('actions', [])]

        task = DootTaskSpec(**core_data, extra=TomlGuard(extra_data))
        return task

    @staticmethod
    def from_name(name:DootTaskName):
        match name:
            case DootTaskName() if bool(name.args):
                spec_dict = name.args.copy()
                spec_dict['name'] = str(name)
                return DootTaskSpec.from_dict(spec_dict)
            case DootTaskName():
                return DootTaskSpec.from_dict({"name": name})
            case _:
                raise TypeError("Bad Type used to build a task spec", name)

    def specialize_from(self, data:DootTaskSpec) -> DootTaskSpec:
        """
          Specialize an existing task spec, with additional data
        """
        if not self.name == data.ctor:
            raise doot.errors.DootTaskTrackingError("Tried to specialize a task that isn't based on this task", str(data.name), str(self.name))
        specialized = {}
        for field in DootTaskSpec.__annotations__.keys():
            match field:
                case "name":
                    specialized[field] = data.name.specialize()
                case "extra":
                   specialized[field] = TomlGuard.merge(data.extra, self.extra, shadow=True)
                case "ctor":
                    specialized[field] = self.ctor
                case "actions":
                    specialized[field] = self.actions + data.actions
                case "depends_on":
                    specialized["depends_on"] = self.depends_on[:] + data.depends_on[:]
                case "required_for":
                    specialized["required_for"] = self.required_for[:] + data.required_for[:]
                case "inject":
                    specialized["inject"] = self.inject[:] + data.inject[:]
                case _:
                    # prefer the newest data, then the unspecialized data, then the default
                    field_data         = DootTaskSpec.__dataclass_fields__.get(field)
                    match getattr(data,field), field_data.default, field_data.default_factory:
                        case x, _MISSING_TYPE(), y if y == TomlGuard:
                            value = TomlGuard.merge(getattr(data,field), getattr(self, field), shadow=True)
                        case x, _MISSING_TYPE(), _MISSING_TYPE():
                            value = x or getattr(self, field)
                        case x, y, _MISSING_TYPE() if x == y:
                            value = getattr(self, field)
                        case x, _, _MISSING_TYPE():
                            value = x
                        case x, _MISSING_TYPE(), _ if bool(x):
                            value = x
                        case x, _MISSING_TYPE(), _:
                            value = getattr(self, field)
                        case x, y, z:
                            raise TypeError("Unknown Task Spec Specialization field types", field, x, y, z)

                    specialized[field] = value

        logging.debug("Specialized Task: %s on top of: %s", data.name, self.name)
        return DootTaskSpec.from_dict(specialized)

    def build(self, ensure=Any):
        task_ctor = self.ctor.try_import(ensure=ensure)
        return task_ctor(self)

    def check(self, ensure=Any):
        if self.ctor.module == "default":
            return True
        self.ctor.try_import(ensure=ensure)
        return True

    def __hash__(self):
        return hash(str(self.name))
