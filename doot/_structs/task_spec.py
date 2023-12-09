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
from tomlguard import TomlGuard
import doot.errors
import doot.constants as consts
from doot.enums import TaskFlags, ReportEnum, StructuredNameEnum
from doot._structs.structured_name import DootStructuredName
from doot._structs.action_spec import DootActionSpec
from doot._structs.artifact import DootTaskArtifact

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]

def _prepare_deps(deps:None|list[str], source=None) -> list[DootTaskArtifact|DootStructuredName]:
    """
      Prepares dependencies, converting from strings to Artifacts (ie:files), or Task Names
    """
    if deps is None:
        return []

    results = []
    for x in deps:
        if x.startswith(consts.FILE_DEP_PREFIX):
            results.append(DootTaskArtifact(pl.Path(x.removeprefix(consts.FILE_DEP_PREFIX))))
        elif consts.TASK_SEP in x:
            results.append(DootStructuredName.from_str(x))
        else:
            raise doot.errors.DootInvalidConfig("Unrecognised task pre/post dependency form. (Remember: files are prefixed with `file://`, tasks are in the form group::name)", x, source)


    return results


@dataclass
class DootTaskSpec:
    """ The information needed to describe a generic task

    actions : list[ [args] | {do="", args=[], **kwargs} ]
    """
    name              : DootStructuredName                           = field()
    doc               : list[str]                                    = field(default_factory=list)
    source            : DootStructuredName|str|None                  = field(default=None)
    actions           : list[Any]                                    = field(default_factory=list)

    required_for      : list[DootTaskArtifact]                       = field(default_factory=list)
    depends_on        : list[DootTaskArtifact]                       = field(default_factory=list)
    priority          : int                                          = field(default=10)
    ctor_name         : DootStructuredName                           = field(default=None)
    ctor              : type|Callable|None                           = field(default=None)
    # Any additional information:
    version            : str                                         = field(default="0.1")
    print_levels       : TomlGuard                                      = field(default_factory=TomlGuard)
    flags              : TaskFlags                                   = field(default=TaskFlags.TASK)

    extra              : TomlGuard                                      = field(default_factory=TomlGuard)

    inject             : list[str]                                   = field(default_factory=list) # For taskers
    @staticmethod
    def from_dict(data:dict, *, ctor:type=None, ctor_name=None):
        """ builds a task spec from a raw dict
          able to handle a name:str = "group::task" form,
          able to convert TaskFlag str's into an or'd enum value
          """
        core_keys = list(DootTaskSpec.__dataclass_fields__.keys())
        core_data   = {}
        extra_data  = {}

        # Integrate extras, normalize keys
        for key, val in data.items():
            match key:
                case "extra":
                    extra_data.update(dict(val))
                case "print_levels":
                    core_data[key] = TomlGuard(val)
                case "required_for" | "depends_on" | "required-for" | "depends-on":
                    processed = _prepare_deps(val)
                    core_data[key.replace("-","_")] = processed
                case x if x in core_keys:
                    core_data[x] = val
                case x if x.replace("-", "_") in core_keys:
                    core_data[x.replace("-", "_")] = val
                case x if x not in ["name", "group"]:
                    extra_data[key] = val

        # Construct group and name
        match data:
            case {"group": group, "name": str() as name}:
                core_data['name']  = DootStructuredName(data['group'], data['name'])
            case {"name": str() as name}:
                core_data['name'] = DootStructuredName.from_str(name)
            case {"name": DootStructuredName() as name}:
                core_data['name'] = name
            case _:
                core_data['name'] = DootStructuredName(None, None)

        # Check flags are valid
        if 'flags' in data and any(x not in TaskFlagNames for x in data.get('flags', [])):
            logging.warning("Unknown Task Flag used, check the spec for %s in %s", core_data['name'], data.get('source', ''))

        core_data['flags'] = ftz.reduce(lambda x,y: x|y, map(lambda x: TaskFlags[x],  filter(lambda x: x in TaskFlagNames, core_data.get('flags', ["TASK"]))))

        # Prepare constructor name
        core_data['ctor']  = ctor or core_data.get('ctor', None)
        if ctor_name is not None:
            core_data['ctor_name']      = DootStructuredName.from_str(ctor_name, form=StructuredNameEnum.CLASS)
        elif ctor is not None:
            core_data['ctor_name']      = DootStructuredName(ctor.__module__, ctor.__name__, form=StructuredNameEnum.CLASS)
        else:
            core_data['ctor_name']      = DootStructuredName.from_str(doot.constants.DEFAULT_PLUGINS['tasker'][0][1], form=StructuredNameEnum.CLASS)

        # prep actions
        core_data['actions'] = [DootActionSpec.from_data(x) for x in core_data.get('actions', [])]

        # prep dependencies:


        return DootTaskSpec(**core_data, extra=TomlGuard(extra_data))

    def specialize_from(self, data:DootTaskSpec) -> DootTaskSpec:
        """
          Specialize an existing task spec, with additional data
        """
        specialized = {}
        for field in DootTaskSpec.__annotations__.keys():
            match field:
                case "name":
                    specialized[field] = data.name
                case "extra":
                   specialized[field] = TomlGuard.merge(data.extra, self.extra, shadow=True)
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
        return DootTaskSpec(**specialized)

    def __hash__(self):
        return hash(str(self.name))




"""


"""
