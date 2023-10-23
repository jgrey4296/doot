#!/usr/bin/env python3
"""

"""
##-- default imports
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

##-- end default imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

import importlib
import doot
import doot.errors
import doot.constants
from doot._abstract import Command_i, PluginLoader_p
from doot.structs import TaskStub, DootStructuredName
from doot.task.base_tasker import DootTasker
from doot.task.base_task import DootTask
from collections import defaultdict

##-- data
data_path = doot.constants.TOML_TEMPLATE
##-- end data

class StubCmd(Command_i):
    """ Called to interactively create a stub task definition
      with a `target`, outputs to that file, else to stdout for piping
    """
    _name      = "stub"
    _help      = ["Create a new stub task either to stdout, or path"]

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            self.make_param("file-target", type=str,     default=""),
            self.make_param("Config",                    default=False,     desc="Stub a doot.toml",                  prefix="--"),
            self.make_param("Types",                     default=False,     desc="List the types of task available", prefix="--"),
            self.make_param("Actions",                   default=False,     desc="Help Stub Actions", prefix="--"),
            self.make_param("Flags",                     default=False,     desc="Help Stub Task Flags", prefix="--"),
            self.make_param("name",        type=str,     default="stub::stub",    desc="The Name of the new task",                   positional=True),
            self.make_param("ctor",        type=str,     default="task",   desc="The short type name of the task generator",  positional=True),
            self.make_param("suppress-header",           default=True, invisible=True)
            ]

    def __call__(self, tasks:Tomler, plugins:Tomler):
        match dict(doot.args.cmd.args):
            case {"Types": True}:
                self._print_types(plugins)
            case {"Config": True}:
                self._stub_doot_toml()
            case {"Actions": True}:
                self._stub_actions()
            case {"Flags": True}:
                self._stub_flags()
            case _:
                self._stub_task_toml(tasks, plugins)

    def _print_types(self, plugins):
        printer.info("Available Tasker Types:")
        for type in set(map(lambda x: x.name, plugins.tasker)):
            printer.info(f"- {type}")

    def _stub_doot_toml(self):
        logging.info("Building Doot Toml Stub")
        doot_toml = pl.Path("doot.toml")
        if doot_toml.exists():
            logging.error("Can't stub doot.toml, it already exists")
            return

        data_text = data_path.read_text()
        with open(task_file, "a") as f:
            f.write(data_text)

        printer.info("doot.toml stub")


    def _import_task_class(self, ctor_name):
        try:
            module_name, cls_name = ctor_name.split(doot.constants.IMPORT_SEP)
            module = importlib.import_module(module_name)
            return getattr(module, cls_name)
        except ImportError as err:
            raise doot.errors.DootTaskLoadError(ctor_name)


    def _stub_task_toml(self, tasks, plugins):
        logging.info("Building Task Toml Stub")
        task_iden                   : str    = doot.args.on_fail("task").cmd.args.ctor()
        task_import_path            : str    = PluginLoader_p.get_loaded("tasker", task_iden) or task_iden
        task_type                   : type   = self._import_task_class(task_import_path)

        # Create stub toml
        stub = TaskStub(ctor=task_iden)
        stub['print_level'].default = "INFO"
        stub['priority'].default = 10
        stub['name'].default = DootStructuredName.from_str(doot.args.cmd.args.name)

        # add ctor specific fields,
        # such as for globber: roots [], exts [], recursive bool, subtask "", head_task ""
        for cls in reversed(task_type.mro()):
            try:
                cls.stub_class(stub)
            except NotImplementedError:
                pass
            except AttributeError:
                pass

        original_name = stub['name'].default.task_str()
        while str(stub['name'].default) in tasks:
            stub['name'].default.task.append("$conflicted$")

        if original_name != stub['name'].default.task_str():
            logging.warning("Group %s: Name %s already defined, trying to modify name to: %s",
                            stub['name'].default.group_str(),
                            original_name,
                            stub['name'].default.task_str())

        # Output to printer/stdout, or file
        if doot.args.cmd.args.file_target == "":
            printer.info(stub.to_toml())
            return

        task_file = pl.Path(doot.args.cmd.args.file_target)
        if task_file.is_dir():
            task_file /= "stub_tasks.toml"
        printer.info("Stubbing task %s into file: %s", stub['name'], task_file)
        with open(task_file, "a") as f:
            f.write("\n")
            f.write(stub.to_toml())

    def _stub_locations(self, tasks, plugins):
        raise NotImplementedError()

    def _stub_actions(self):
        raise NotImplementedError()

    def _stub_flags(self):
        raise NotImplementedError()
