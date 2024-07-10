#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import abc
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
from collections import defaultdict
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from importlib.resources import files
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 1st party imports
import doot
import doot.enums
import doot.errors
from doot.structs import DKeyed
from doot._abstract import PluginLoader_p, Task_i
from doot._structs.dkey import DKey
from doot.cmds.base_cmd import BaseCommand
from doot.structs import CodeReference, TaskName, TaskStub
from doot.task.base_job import DootJob
from doot.task.base_task import DootTask
from doot.utils.decorators import DecorationUtils

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

##-- data
data_path = files(doot.constants.paths.TEMPLATE_PATH).joinpath(doot.constants.paths.TOML_TEMPLATE)
##-- end data
PRINT_LOCATIONS : Final[list[str]] = doot.constants.printer.PRINT_LOCATIONS

class StubCmd(BaseCommand):
    """ Called to interactively create a stub task definition
      with a `target`, outputs to that file, else to stdout for piping
    """
    _name      = "stub"
    _help      = ["Create a new stub task either to stdout, or path"]

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            self.build_param(name="file-target", type=str,     default=""),
            self.build_param(name="Config",                    default=False,           desc="Stub a doot.toml",                  prefix="-"),
            self.build_param(name="Actions",                   default=False,           desc="Help Stub Actions",                 prefix="-"),
            self.build_param(name="cli",                       default=False,           desc="Generate a stub cli arg dict",      prefix="-"),
            self.build_param(name="printer",                   default=False,           desc="Generate a stub cli arg dict",      prefix="-"),

            self.build_param(name="Flags",                     default=False,           desc="Help Stub Task Flags",              prefix="-"),

            self.build_param(name="name",        type=str,     default=None,            desc="The Name of the new task",                          positional=True),
            self.build_param(name="ctor",        type=str,     default="task",          desc="The short type name of the task generator",         positional=True),
            self.build_param(name="suppress-header",           default=True, invisible=True)
            ]

    def _import_task_class(self, ctor_name):
        try:
            code_ref = CodeReference.build(ctor_name)
            return code_ref.try_import()
        except ImportError as err:
            raise doot.errors.DootTaskLoadError(ctor_name)

    def __call__(self, tasks:TomlGuard, plugins:TomlGuard):
        match dict(doot.args.cmd.args):
            case {"Config": True}:
                self._stub_doot_toml()
            case {"Actions": True}:
                self._stub_actions(plugins)
            case {"cli": True}:
                self._stub_cli_arg()
            case {"Flags": True}:
                self._list_flags()
            case _:
                self._stub_task_toml(tasks, plugins)

    def _stub_doot_toml(self):
        logging.info("Building Doot Toml Stub")
        doot_toml = pl.Path("doot.toml")
        data_text = data_path.read_text()
        if doot_toml.exists():
            printer.info(data_text)
            printer.warning("doot.toml it already exists, printed to stdout instead")
            return

        with open(task_file, "a") as f:
            f.write(data_text)

        printer.info("doot.toml stub")

    def _stub_task_toml(self, tasks, plugins):
        """
        This creates a toml stub using default values, as best it can
        """
        logging.info("Building Task Toml Stub")
        task_iden                   : CodeReference       = CodeReference.from_alias(doot.args.on_fail("task").cmd.args.ctor(), "task", plugins)

        if (name:=doot.args.on_fail((None,)).cmd.args.name()) is None:
            raise doot.errors.DootCommandError("No Name Provided for Stub")

        # Create stub toml, with some basic information
        stub                          = TaskStub(ctor=task_iden)
        try:
            stub['name'].default          = TaskName.build(name)
        except ValueError:
            raise doot.errors.DootError("Provide a valid TaskName")

        # add ctor specific fields,
        # such as for dir_walker: roots [], exts [], recursive bool, subtask "", head_task ""
        # works *towards* the task_type, not away, so more specific elements are added over the top of more general elements
        try:
            task_mro = task_iden.try_import().mro()
        except TypeError as err:
            logging.error(err.args[0].replace("\n", ""))
            task_mro = []
            return

        for cls in reversed(task_mro):
            try:
                cls.stub_class(stub)
                if issubclass(cls, Task_i):
                    stub['version'].default         = doot.__version__
                    stub['doc'].default             = []
            except NotImplementedError:
                pass
            except AttributeError:
                pass

        # Convert to alises
        base_a, mixin_a= task_iden.to_aliases("task", plugins)
        stub['ctor'].default   = base_a

        # extend the name if there are already tasks with that name
        original_name = stub['name'].default.task
        while str(stub['name'].default) in tasks:
            stub['name'].default.tail.append("$conflicted$")

        if original_name != stub['name'].default.task:
            logging.warning("Group %s: Name %s already defined, trying to modify name to: %s",
                            stub['name'].default.group,
                            original_name,
                            stub['name'].default.task)

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

    def _stub_actions(self, plugins):
        matched = [x for x in plugins.action if x.name == doot.args.cmd.args.name or x.value == doot.args.cmd.args.name]
        if bool(matched):
            loaded = matched[0].load()
            printer.info("- Action %s : %s", matched[0].name, matched[0].value)
            match getattr(loaded, "_toml_help", []):
                case []:
                    pass
                case [*xs]:
                    for x in xs:
                        printer.info(x)

            loaded = getattr(loaded, "__call__", loaded)
            match DKeyed.get_keys(loaded):
                case []:
                    printer.info("-- No Declared Kwargs")
                case [*xs]:
                    printer.info("-- Declared kwargs for action: %s", sorted([repr(x) for x in xs]))
        else:
            printer.info("Available Actions:")
            for action in sorted(plugins.action, key=lambda x: x.name):
                printer.info("-- %10s : %s", action.name, action.value)

        printer.info("")
        printer.info("-- Toml Form: ")
        # TODO customize this with declared annotations
        if bool(matched):
            printer.info("{ do=\"%s\", args=[] } # plus any kwargs a specific action uses", matched[0].name)
        else:
            printer.info("{ do=\"action name/import path\", args=[], inState=[], outState=[] } # plus any kwargs a specific action uses")

        printer.info("")
        printer.info("- For Custom Python Actions, implement the following in the .tasks directory")
        printer.info("def custom_action(spec:ActionSpec, task_state:dict) -> None|bool|dict:...")

    def _stub_cli_arg(self):
        printer.info("# - CLI Arg Form. Add to task spec: cli=[]")
        printer.info("")
        stub = []
        stub.append('name="')
        stub.append(doot.args.on_fail("default").cmd.args.name())
        stub.append('", ')
        stub.append('type="str", ')
        stub.append('prefix="-", ')
        stub.append('default="", ')
        stub.append('desc="", ')
        stub.append('positional=false ')

        printer.info("{ %s }", "".join(stub))

    def _list_flags(self):
        printer.info("Task Flags: ")
        for x in sorted(doot.enums.TaskMeta_f, key=lambda x: x.name):
            printer.info("-- %s", x.name)
