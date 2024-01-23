#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

# import abc
# import datetime
# import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)

# from uuid import UUID, uuid1
# from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

from collections import ChainMap
import importlib
import tomlguard
import doot
import doot.errors
from doot.structs import DootTaskSpec, DootTaskName, DootCodeReference
from doot.constants import DEFAULT_TASK_GROUP, IMPORT_SEP
from doot._abstract import TaskLoader_p, Job_i, Task_i, TaskBase_i

TASK_STRING : Final[str]  = "task_"
prefix_len  : Final[int]  = len(TASK_STRING)

task_sources              = doot.config.on_fail([".tasks"], list).settings.tasks.sources(wrapper=lambda x: [doot.locs[y] for y in x])
allow_overloads           = doot.config.on_fail(False, bool).allow_overloads()

def apply_group_and_source(group, source, x):
    x['group']  = x.get('group', group)
    x['source'] = str(source)
    return x


@doot.check_protocol
class DootTaskLoader(TaskLoader_p):
    """
    load toml defined tasks, and create doot.structs.DootTaskSpecs of them
    """
    tasks         : dict[str, tuple(dict, Job_i)] = {}
    cmd_names     : set[str]                         = set()
    task_builders : dict[str,Any]                    = dict()
    extra : TomlGuard

    def setup(self, plugins, extra=None) -> Self:
        logging.debug("---- Registering Task Builders")
        self.cmd_names     = set(map(lambda x: x.name, plugins.get("command", [])))
        self.tasks         = {}
        self.plugins       = plugins
        self.task_builders = {}
        for plugin in tomlguard.TomlGuard(plugins).on_fail([]).task():
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
            case dict() | tomlguard.TomlGuard():
                self.extra = tomlguard.TomlGuard(extra).on_fail({}).tasks()
        logging.debug("Task Loader Setup with %s extra tasks", len(self.extra))
        return self


    def load(self) -> TomlGuard[tuple[dict, type[Task_i|Job_i]]]:
        start_time = time.perf_counter()
        logging.debug("---- Loading Tasks")
        raw_specs : list[dict] = []
        logging.debug("Loading Tasks from Config")
        for source in doot._configs_loaded_from:
            try:
                source_data : TomlGuard = tomlguard.load(source)
            except OSError as err:
                logging.error("Failed to Load Config File: %s : %s", source, err.args)
                continue

            task_specs = source_data.on_fail({}).tasks()
            raw_specs += self._load_raw_specs(task_specs, source)


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

        # Reapply config location declarations as overrides:
        for loc in doot.config.on_fail([]).locations():
            doot.locs.update(loc, strict=False)

        logging.debug("Task List Size: %s", len(self.tasks))
        logging.debug("Task List Names: %s", list(self.tasks.keys()))
        logging.debug("---- Tasks Loaded in %s seconds", f"{time.perf_counter() - start_time:0.4f}")
        return tomlguard.TomlGuard(self.tasks)

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
        # Load task spec path
        if not path.exists():
            pass
        elif path.is_dir():
            for task_file in [x for x in path.iterdir() if x.suffix == ".toml"]:
                try:
                    data = tomlguard.load(task_file)
                except OSError as err:
                    logging.error("Failed to Load Task File: %s", task_file)
                    continue

                for group, val in data.on_fail({}).tasks().items():
                    # sets 'group' for each task if it hasn't been set already
                    raw_specs += map(ftz.partial(apply_group_and_source, group, task_file), val)
                logging.info("Loaded Tasks from: %s", task_file)
                if 'locations' in data:
                    self._load_location_updates(data.locations, task_file)

        elif path.is_file():
            try:
                data = tomlguard.load(path)
            except OSError:
                logging.error("Failed to Load Task File: %s", path)
                return raw_specs

            for group, val in data.on_fail({}).tasks().items():
                # sets 'group' for each task if it hasn't been set already
                raw_specs += map(ftz.partial(apply_group_and_source, group, path), val)
            logging.info("Loaded Tasks from: %s", path)
            if 'locations' in data:
                self._load_location_updates(data.locations, path)

        return raw_specs


    def _build_task_specs(self, group_specs:list[dict], command_names) -> list[DootTaskSpec]:
        """
        convert raw dicts into DootTaskSpec objects,
          checking nothing tries to shadow a command name or other task name
        """
        task_descriptions : dict[str, DootTaskSpec] = {}
        dont_allow_overloads = lambda task_name, group_name: not allow_overloads and task_name in task_descriptions and group_name == task_descriptions[task_name][0]['group']
        for spec in group_specs:
            task_alias = "task"
            try:
                match spec:
                    case {"name": task_name, "disable" : True}: # Disabled specs
                        logging.info("Spec is disabled: %s", task_name)
                    # case {"name": task_name} if task_name in command_names:
                    #     raise doot.errors.DootTaskLoadError("Name conflict: %s is already a Command", task_name)
                    case {"name": task_name, "group": group} if dont_allow_overloads(task_name, group): # complain on overload
                        raise doot.errors.DootTaskLoadError("Task Name Overloaded: %s : %s", task_name, group)
                    case {"name": task_name, "ctor": str() as task_alias} if task_alias in self.task_builders: # build named plugin type
                        logging.info("Building Task from short name: %s : %s", task_name, task_alias)
                        task_iden                   : DootCodeReference       = DootCodeReference.from_alias(task_alias, "task", self.plugins)
                        task_iden_with_mixins       : DootCodeReference       = task_iden.add_mixins(*spec.get("mixins", []), plugins=self.plugins)
                        spec['ctor'] = task_iden_with_mixins
                        task_spec = DootTaskSpec.from_dict(spec)
                        if str(task_spec.name) in task_descriptions:
                            logging.warning("Overloading Task: %s : %s", str(task_spec.name), task_alias)

                        task_spec.check(ensure=TaskBase_i)
                        task_descriptions[str(task_spec.name)] = task_spec
                    case {"name": task_name}:
                        logging.info("Building Task: %s", task_name)
                        task_spec = DootTaskSpec.from_dict(spec)
                        if str(task_spec.name) in task_descriptions:
                            logging.warning("Overloading Task: %s : %s", str(task_spec.name), str(task_spec.ctor))

                        task_spec.check(ensure=TaskBase_i)
                        task_descriptions[str(task_spec.name)] = task_spec

                    case _: # Else complain
                        raise doot.errors.DootTaskLoadError("Task Spec missing, at least, a name and ctor: %s: %s", spec['source'], spec)
            except doot.errors.DootLocationError as err:
                logging.debug(err)
                raise doot.errors.DootTaskLoadError("Task Spec '%s' Load Failure: Missing Location: '%s'. Source File: %s", task_name, str(err), spec['source']) from err
            except ModuleNotFoundError as err:
                logging.debug(err)
                raise doot.errors.DootTaskLoadError("Task Spec '%s' Load Failure: Bad Module Name: '%s'. Source File: %s", task_name, task_alias, spec['source']) from err
            except AttributeError as err:
                logging.debug(err)
                raise doot.errors.DootTaskLoadError("Task Spec '%s' Load Failure: Bad Class Name: '%s'. Source File: %s", task_name, task_alias, spec['source'], err.args) from err
            except ValueError as err:
                logging.debug(err)
                raise doot.errors.DootTaskLoadError("Task Spec '%s' Load Failure: Module/Class Split failed on: '%s'. Source File: %s", task_name, task_alias, spec['source']) from err
            except TypeError as err:
                logging.debug(err)
                raise doot.errors.DootTaskLoadError("Task Spec '%s' Load Failure: Bad Type constructor: '%s'. Source File: %s", task_name, spec['ctor'], spec['source']) from err
            except ImportError as err:
                logging.debug(err)
                raise doot.errors.DootTaskLoadError("Task Spec '%s' Load Failure: ctor import check failed. Source File: %s", task_name, spec['source']) from err

        return task_descriptions

    def _load_location_updates(self, data:list[TomlGuard], source):
        logging.debug("Loading Location Updates: %s", source)
        for group in data:
            try:
                doot.locs.update(group)
            except KeyError as err:
                doot.printer.warning("Locations Already Defined: %s : %s", err.args[1], source)
