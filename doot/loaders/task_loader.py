#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from collections import ChainMap
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
from jgdv.structs.strang.errors import LocationError

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import Job_i, Task_i, TaskLoader_p
from doot.structs import TaskName, TaskSpec

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

DEFAULT_TASK_GROUP        = doot.constants.names.DEFAULT_TASK_GROUP
IMPORT_SEP                = doot.constants.patterns.IMPORT_SEP
TASK_STRING : Final[str]  = "task_"
prefix_len  : Final[int]  = len(TASK_STRING)

task_sources              = doot.config.on_fail([doot.locs.Current[".tasks"]], list).settings.tasks.sources(wrapper=lambda x: [doot.locs[y] for y in x])
allow_overloads           = doot.config.on_fail(False, bool).allow_overloads()

def apply_group_and_source(group, source, x):
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
    cmd_names     : set[str]                         = set()
    task_builders : dict[str,Any]                    = dict()
    extra         : ChainGuard

    def setup(self, plugins, extra=None) -> Self:
        logging.debug("---- Registering Task Builders")
        self.cmd_names     = set(map(lambda x: x.name, plugins.get("command", [])))
        self.tasks         = {}
        self.plugins       = plugins
        self.task_builders = {}
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
            raw_specs : list[dict] = []
            logging.debug("Loading Tasks from Config")
            for source in doot._configs_loaded_from:
                try:
                    source_data : ChainGuard = ChainGuard.load(source)
                    task_specs = source_data.on_fail({}).tasks()
                    raw_specs += self._load_raw_specs(task_specs, source)
                except OSError as err:
                    logging.error("Failed to Load Config File: %s : %s", source, err.args)
                    continue

            if self.extra:
                logging.debug("Loading Tasks from extra values")
                raw_specs += self._load_raw_specs(self.extra, "(extra)")

            logging.debug("Loading tasks from sources: %s", [str(x) for x in task_sources])
            for path in task_sources:
                raw_specs += self._load_specs_from_path(path)

            logging.debug("Loaded %s Task Specs", len(raw_specs))
            if bool(self.tasks):
                logging.warning("Task Loader is overwriting already loaded tasks")
            self.tasks = self._build_task_specs(raw_specs, self.cmd_names)

        logging.debug("Task List Size: %s", len(self.tasks))
        logging.debug("Task List Names: %s", list(self.tasks.keys()))
        return ChainGuard(self.tasks)

    def _load_raw_specs(self, data:dict, source:pl.Path|Literal['(extra)']) -> list[dict]:
        """ extract raw task descriptions from a toplevel tasks dict, with not format checking
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

    def _load_specs_from_path(self, path) -> list[dict]:
        """ load a config file defined task_sources of tasks """
        raw_specs = []

        targets = []
        if path.is_dir():
            targets += [x for x in path.iterdir() if x.suffix == ".toml"]
        elif path.is_file():
            targets.append(path)
        else:
            assert(not path.exists())

        for task_file in targets:
            try:
                data = ChainGuard.load(task_file)
            except OSError as err:
                logging.error("Failed to Load Task File: %s : %s", task_file, err.filename)
                continue
            else:
                for group, val in data.on_fail({}).tasks().items():
                    # sets 'group' for each task if it hasn't been set already
                    raw_specs += map(ftz.partial(apply_group_and_source, group, task_file), val)
                logging.info("Loaded Tasks from: %s", task_file)
                self._load_location_updates(data.on_fail([]).locations(), task_file)

        else:
            return raw_specs

    def _build_task_specs(self, group_specs:list[dict], command_names:set[str]) -> dict[str, TaskSpec]:
        """
        convert raw dicts into TaskSpec objects,
          checking nothing tries to shadow a command name or other task name
        """
        logging.info("---- Building Task Specs")
        task_descriptions : dict[str, TaskSpec] = {}

        def detect_overloads(task_name,  group_name):
            if task_name not in task_descriptions:
                return False

            return group_name == task_descriptions[task_name][0]['group']

        failures                                = []
        for spec in group_specs:
            task_alias = "task"
            task_spec = None
            try:
                match spec:
                    case {"name": task_name, "group": group} if not allow_overloads and detect_overloads(task_name, group): # complain on overload
                        raise doot.errors.DootTaskLoadError("Task Name Overloaded: %s : %s", task_name, group)
                    case {"name": task_name, "ctor": str() as task_alias} if task_alias in self.task_builders: # build named plugin type
                        logging.debug("Building Task from short name: %s : %s", task_name, task_alias)
                        task_iden                   : CodeReference       = CodeReference.from_value(self.task_builders[task_alias])
                        spec['ctor'] = task_iden
                        task_spec = TaskSpec.build(spec)
                        if str(task_spec.name) in task_descriptions:
                            logging.warning("Overloading Task: %s : %s", str(task_spec.name), task_alias)
                    case {"name": task_name}:
                        logging.debug("Building Task: %s", task_name)
                        task_spec = TaskSpec.build(spec)
                        if str(task_spec.name) in task_descriptions:
                            logging.warning("Overloading Task: %s : %s", str(task_spec.name), str(task_spec.ctor))
                    case _: # Else complain
                        raise doot.errors.DootTaskLoadError("Task Spec missing, at least, needs at least a name and ctor: %s: %s", spec, spec['sources'][0] )
            except LocationError as err:
                logging.warning("Task Spec '%s' Load Failure: Missing Location: '%s'. Source File: %s", spec['name'], str(err), spec['sources'][0])
            except ModuleNotFoundError as err:
                failures.append(err)
                logging.debug(err)
                logging.error("Task Spec '%s' Load Failure: Bad Module Name: '%s'. Source File: %s", spec['name'], task_alias, spec['sources'][0])
            except AttributeError as err:
                failures.append(err)
                logging.debug(err)
                logging.error("Task Spec '%s' Load Failure: Bad Class Name: '%s'. Source File: %s", spec['name'], task_alias, spec['sources'][0], err.args)
            except ValueError as err:
                failures.append(err)
                logging.debug(err)
                logging.error("Task Spec '%s' Load Failure: '%s'. Source File: %s. Message:\n %s", spec['name'], task_alias, spec['sources'][0], str(err))
            except TypeError as err:
                failures.append(err)
                logging.debug(err)
                logging.error("Task Spec '%s' Load Failure: Bad Type constructor: '%s'. Source File: %s", spec['name'], spec['ctor'], spec['sources'][0])
            except ImportError as err:
                failures.append(err)
                logging.debug(err)
                logging.error("Task Spec '%s' Load Failure: ctor import check failed. Source File: %s", spec['name'], spec['sources'][0])
            else:
                assert(task_spec is not None)
                task_descriptions[str(task_spec.name)] = task_spec
        else:
            if bool(failures):
                raise doot.errors.DootTaskLoadError("Loading Task Specs Encountered Errors",  len(failures))

            return task_descriptions

    def _load_location_updates(self, data:list[ChainGuard], source):
        logging.debug("Loading Location Updates: %s", source)
        for group in data:
            try:
                doot.locs.Current.update(group, strict=False)
            except KeyError as err:
                printer.warning("Locations Already Defined: %s : %s", err.args[1], source)
            except TypeError as err:
                printer.warning("Location failed to validate: %s : %s", err.args[1], source)
