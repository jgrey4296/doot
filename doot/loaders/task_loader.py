#!/usr/bin/env python3
"""

"""
# ruff: noqa: FBT003
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import re
import time
import types
import typing
from collections import ChainMap, defaultdict
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match, Self, Literal,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.strang import CodeReference
from jgdv.util.time_ctx import TimeCtx
from jgdv.structs.locator.errors import LocationError, StrangError
from pydantic import ValidationError
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import Job_i, Task_i, TaskLoader_p
from doot.structs import TaskName, TaskSpec

# ##-- end 1st party imports

# ##-- typecheck imports
# isort: off
if typing.TYPE_CHECKING:
    import pathlib as pl
    from jgdv import Maybe


# isort: on
# ##-- end typecheck imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

DEFAULT_TASK_GROUP        = doot.constants.names.DEFAULT_TASK_GROUP
IMPORT_SEP                = doot.constants.patterns.IMPORT_SEP
TASK_STRING : Final[str]  = "task_"
prefix_len  : Final[int]  = len(TASK_STRING)

task_sources              = doot.config.on_fail([doot.locs.Current[".tasks"]], list).startup.sources.tasks.sources(wrapper=lambda x: [doot.locs[y] for y in x])
allow_overloads           = doot.config.on_fail(False, bool).allow_overloads()

def apply_group_and_source(group, source, x): # noqa: ANN201, ANN001
    match x:
        case ChainGuard():
            x = dict(x.items())
            x['group']  = x.get('group', group)
            if 'sources' not in x:
                x['sources'] = []
            x['sources'].append(str(source))
        case dict():
            x['group']  = x.get('group', group)
            if 'sources' not in x:
                x['sources'] = []
            x['sources'].append(str(source))
    return x

@doot.check_protocol
class DootTaskLoader(TaskLoader_p):
    """
    load toml defined tasks, and create doot.structs.TaskSpecs of them
    """
    tasks         : dict[str, tuple(dict, Job_i)]    = {}
    failures      : dict[str, list]                  = defaultdict(list)
    cmd_names     : set[str]                         = set()
    task_builders : dict[str,Any]                    = dict()
    extra         : ChainGuard

    def setup(self, plugins, extra=None) -> Self:
        logging.debug("---- Registering Task Builders")
        self.cmd_names     = set(map(lambda x: x.name, plugins.get("command", [])))
        self.tasks         = {}
        self.plugins       = plugins
        self.task_builders = {}
        self.failures      = defaultdict(list)
        for plugin in ChainGuard(plugins).on_fail([]).task():
            if plugin.name in self.task_builders:
                logging.warning("Conflicting Task Builder Type Name: %s: %s / %s",
                                plugin.name,
                                self.task_builders[plugin.name],
                                plugin)
                continue

            try:
                self.task_builders[plugin.name] = plugin.load()
                logging.info("Registered Task Builder short name: %s", plugin.name)
            except ModuleNotFoundError as err:
                logging.warning(f"Bad Task Builder Plugin Specified: %s", plugin)
        else:
            logging.debug("Registered Task Builders: %s", self.task_builders.keys())

        match extra: # { group : [task_dicts] }
            case None:
                self.extra = {}
            case list():
                self.extra = {"_": extra}
            case dict() | ChainGuard():
                self.extra = ChainGuard(extra).on_fail({}).tasks()
        logging.debug("Task Loader Setup with %s extra tasks", len(self.extra))
        return self

    def load(self) -> ChainGuard[TaskSpec]:
        with TimeCtx(logger=logging, entry_msg="---- Loading Tasks",  exit_msg="---- Task Loading Time"):
            logging.debug("Loading Tasks from Config files")
            for source in doot._configs_loaded_from:
                try:
                    source_data : ChainGuard = ChainGuard.load(source)
                    task_specs = source_data.on_fail({}).tasks()
                except OSError as err:
                    logging.exception("Failed to Load Config File: %s : %s", source, err.args)
                    continue
                else:
                    raw = self._get_raw_specs_from_data(task_specs, source)
                    self._build_task_specs(raw, self.cmd_names)

            if self.extra:
                logging.debug("Loading Tasks from extra values")
                raw = self._get_raw_specs_from_data(self.extra, "(extra)")
                self._build_task_specs(raw, self.cmd_names)


            logging.debug("Loading tasks from sources: %s", [str(x) for x in task_sources])
            for path in task_sources:
                self._load_specs_from_path(path)

        if bool(self.failures):
            raise doot.errors.StructLoadError("Loading Tasks Failed", self.failures)

        logging.debug("Task List Size: %s", len(self.tasks))
        logging.debug("Task List Names: %s", list(self.tasks.keys()))
        return ChainGuard(self.tasks)

    def _get_raw_specs_from_data(self, data:dict, source:pl.Path|Literal['(extra)']) -> list[dict]:
        """ extract raw task descriptions from a toplevel tasks dict, with no format checking.
          expects the dict to be { group_key : [ task_dict ]  }
          """
        raw_specs = []
        # Load from doot.toml task specs
        for group, data in data.items():
            if not isinstance(data, list):
                logging.warning("Unexpected task specification format: %s : %s", group, data)
            else:
                raw_specs += map(ftz.partial(apply_group_and_source, group, source), data)

        logging.info("Loaded Tasks from: %s", source)
        return raw_specs

    def _load_specs_from_path(self, path:pl.Path):
        """ load a config file defined task_sources of tasks """
        targets   = []
        if path.is_dir():
            targets += [x for x in path.iterdir() if x.suffix == ".toml"]
        elif path.is_file():
            targets.append(path)
        else:
            assert(not path.exists())

        for task_file in targets:
            logging.info("Loading Tasks from: %s", task_file)
            try:
                data = ChainGuard.load(task_file)
                doot.verify_config_version(data.on_fail(None).doot_version(), source=task_file)
            except (IOError, OSError) as err:
                self.failures[task_file].append("Failed to Load Toml File")
            except doot.errors.VersionMismatchError as err:
                if "startup" not in data:
                    self.failures[task_file].append("Version mismatch")
            else:
                for update in data.on_fail([]).state():
                    doot.update_global_task_state(update, source=task_file)

                raw_specs = []
                for group, val in data.on_fail({}).tasks().items():
                    # sets 'group' for each task if it hasn't been set already
                    raw_specs += map(ftz.partial(apply_group_and_source, group, task_file), val)

                self._build_task_specs(raw_specs, self.cmd_names, source=task_file)
                self._load_location_updates(data.on_fail([]).locations(), task_file)


    def _build_task_specs(self, specs:list[dict], commands:set[str], source:str|pl.Path=None):
        """
        convert raw dicts into TaskSpec objects

        """
        logging.info("---- Building Task Specs (%s Current)", len(self.tasks))
        source = source or "<Sourceless>"

        def _allow_registration(task_name) -> bool:
            """ precondition to check for overrides/name conflicts """
            logging.info("Checking: %s", task_name)
            if allow_overloads:
                return True
            return task_name not in self.tasks


        for spec in specs:
            logging.info("Processing: %s", spec['name'])
            task_alias = "task"
            task_spec  = None
            try:
                match spec:
                    case {"name": task_name, "ctor": CodeReference() as ctor}:
                        task_spec = TaskSpec.build(spec)
                    case {"name": task_name, "ctor": str() as task_alias} if task_alias in self.task_builders:
                        spec['ctor'] = CodeReference.from_value(self.task_builders[task_alias])
                        task_spec = TaskSpec.build(spec)
                    case {"name": task_name}:
                        task_spec = TaskSpec.build(spec)
                    case _: # Else complain
                        raise doot.errors.StructLoadError("Task Spec missing, at least, needs at least a name and ctor", spec, spec['sources'][0] )
            except ValidationError as err:
                for suberr in err.errors():
                    locs = ", ".join(suberr['loc'])
                    self.failures[source].append(f"({locs}) : '{suberr['input']}' :- {suberr['msg']}")
            except StrangError as err:
                self.failures[source].append(err)
            except LocationError as err:
                self.failures[source].append(err)
            except ModuleNotFoundError as err:
                self.failures[source].append(err)
            except AttributeError as err:
                self.failures[source].append(err)
            except ValueError as err:
                self.failures[source].append(err)
            except TypeError as err:
                self.failures[source].append(err)
            except ImportError as err:
                self.failures[source].append(err)
            else:
                assert(task_spec is not None)
                if _allow_registration(task_spec.name): # complain on overload
                    logging.info("Registering Task: %s", task_spec.name)
                    self.tasks[task_spec.name] = task_spec
                else:
                    logging.warning("Current Tasks: %s", self.tasks)
                    err = doot.errors.StructLoadError("Task Name Overloaded", task_name)
                    self.failures[source].append(err)


    def _load_location_updates(self, data:list[ChainGuard], source):
        logging.debug("Loading Location Updates: %s", source)
        for group in data:
            try:
                doot.locs.Current.update(group, strict=False)
            except KeyError as err:
                printer.warning("Locations Already Defined: %s : %s", err.args[1], source)
            except TypeError as err:
                printer.warning("Location failed to validate: %s : %s", err.args[1], source)
