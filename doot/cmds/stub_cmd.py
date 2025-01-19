#!/usr/bin/env python3
"""

"""
# ruff: noqa: B009
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
import typing
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.enums
import doot.errors
from doot._abstract import PluginLoader_p, Task_i
from doot._structs.dkey import DKey
from doot.cmds.base_cmd import BaseCommand
from doot.structs import DKeyed, TaskName, TaskStub
from doot.task.base_job import DootJob
from doot.task.base_task import DootTask

# ##-- end 1st party imports

# ##-- types
# isort: off
if typing.TYPE_CHECKING:
   from jgdv import Maybe, ChainGuard, Lambda
   type ListVal = str|Lambda|tuple[str,dict]
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
cmd_l   = doot.subprinter("cmd")
##-- end logging

##-- data
data_path = files(doot.constants.paths.TEMPLATE_PATH).joinpath(doot.constants.paths.TOML_TEMPLATE)
##-- end data
PRINT_LOCATIONS : Final[list[str]] = doot.constants.printer.PRINT_LOCATIONS

NL = None

class _StubDoot_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(prefix="--", name="config",  type=bool,    default=False,           desc="Stub a doot.toml"),
                ]

    def _stub_doot_toml(self) -> list[str]:
        logging.info("---- Stubbing Doot Toml")
        doot_toml = pl.Path("doot.toml")
        data_text = data_path.read_text()
        if doot_toml.exists():
            cmd_l.info(data_text)
            cmd_l.warning("doot.toml it already exists, printed to stdout instead")
            return

        with doot_toml.open("a") as f:
            f.write(data_text)

        cmd_l.info("doot.toml stub")

class _StubParam_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(prefix="--", name="param",   type=bool,    default=False,           desc="Generate a stub cli arg dict"),
                ]

    def _stub_cli_param(self) -> list[str]:
        logging.info("---- Printing CLI Arg info")
        result = [
            "# - CLI Arg Form. Add to task spec: cli=[]",
            '{',
            'name="{}",'.format(doot.args.on_fail("default").cmd.args.name()),
            'prefix="-", ',
            'type="str", ',
            'default="",',
            'desc="", ',
            "}",
            ]
        return result

class _StubAction_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(prefix="--", name="action",  type=bool,    default=False,           desc="Help Stub Actions"),
                ]

    def _stub_action(self, plugins) -> list[str]:
        logging.info("---- Stubbing Actions")
        result = []
        target_name = doot.args.cmd.args.name
        unaliased = doot.aliases.on_fail(target_name).action[target_name]
        matched = [x for x in plugins.action
                   if x.name == target_name
                   or x.value == unaliased]
        if bool(matched):
            loaded = matched[0].load()
            result.append("- {} (Action, {})".format(matched[0].name, matched[0].value))
            match getattr(loaded, "_toml_help", []):
                case [] if bool(getattr(loaded, "__doc__")):
                    result.append(loaded.__doc__)
                case []:
                    pass
                case [*xs]:
                    for x in xs:
                        result.append(x)

            loaded = getattr(loaded, "__call__", loaded)
            match DKeyed.get_keys(loaded):
                case []:
                    result.append("-- No Declared Kwargs")
                case [*xs]:
                    result.append("-- Declared kwargs for action: %s", sorted([repr(x) for x in xs]))

        result.append(NL)
        result.append("-- Toml Form of an action: ")
        # TODO customize this with declared annotations
        if bool(matched):
            result.append("{ do=\"%s\", args=[], key=val } " % matched[0].name)
        else:
            result.append("{ do=\"action name/import path\", args=[], inState=[], outState=[] } # plus any kwargs a specific action uses")

        return result

class _StubTask_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(prefix="--", name="task",  type=bool),
                self.build_param(name="out",  type=str,     default=""),

                self.build_param(prefix=1, name="name", type=str, default=None,    desc="The Name of the new task"),
                self.build_param(prefix=2, name="ctor", type=str, default="task",  desc="a code ref, or alias of a task class"),
                ]

    def _stub_task_toml(self, tasks, plugins) -> list[str]:
        """
        This creates a toml stub using default values, as best it can
        """
        logging.info("---- Stubbing Task Toml")
        result = []
        match  doot.aliases.task.get((ctor:=doot.args.on_fail("task").cmd.args.ctor()), None):
            case None:
                raise doot.errors.CommandError("Task Ctor was not appliable", ctor)
            case x:
                task_ctor : CodeReference = CodeReference(x)

        match doot.args.on_fail(None).cmd.args.name():
            case None:
                raise doot.errors.CommandError("No Name Provided for Stub")
            case x:
                name = TaskName(x)

        # Create stub toml, with some basic information
        stub = TaskStub(ctor=task_ctor)
        stub['name'].default          = name

        # add ctor specific fields,
        # such as for dir_walker: roots [], exts [], recursive bool, subtask "", head_task ""
        # works *towards* the task_type, not away, so more specific elements are added over the top of more general elements
        try:
            task_mro = task_ctor().mro()
        except TypeError as err:
            logging.exception(err.args[0].replace("\n", ""))
            task_mro = []
            return

        for cls in reversed(task_mro):
            try:
                cls.stub_class(stub)
                if issubclass(cls, Task_i):
                    stub['doot_version'].default         = doot.__version__
                    stub['doc'].default             = []
            except NotImplementedError:
                pass
            except AttributeError:
                pass

        # Convert to alises
        stub['ctor'].default   = task_ctor

        # extend the name if there are already tasks with that name
        original_name = stub['name'].default[1:]
        while str(stub['name'].default) in tasks:
            stub['name'].default.tail.append("$conflicted$")

        if original_name != stub['name'].default[1:]:
            logging.warning("Group %s: Name %s already defined, trying to modify name to: %s",
                            stub['name'].default[0:],
                            original_name,
                            stub['name'].default[1:])

        # Output to printer/stdout, or file
        if doot.args.cmd.args.out == "":
            result.append(stub.to_toml())
            return result

        task_file = pl.Path(doot.args.cmd.args.out)
        if task_file.is_dir():
            task_file /= "stub_tasks.toml"
        cmd_l.user("Stubbing task %s into file: %s", stub['name'], task_file)
        with task_file.open("a") as f:
            f.write("\n")
            f.write(stub.to_toml())

class _StubPrinter_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(prefix="--", name="printer", type=bool,    default=False,           desc="Generate a stub printer config"),
                ]

    def _stub_printer(self) -> list[str]:
        logging.info("---- Printing Printer Spec Info")
        result = [
            ("- Printer Config Spec Form. Use in doot.toml [logging], [logging.subprinters], and [logging.extra]", {"colour":"blue"}),
            NL,
            'NAME = { level="", filter=[], target=[""], format="", colour=true, propagate=false, filename_fmt=""}',
        ]
        return result

class StubCmd(_StubDoot_m, _StubParam_m, _StubAction_m, _StubTask_m, _StubPrinter_m, BaseCommand):
    """ Called to interactively create a stub task definition
      with a `target`, outputs to that file, else to stdout for piping
    """
    _name      = "stub"
    _help      = ["Create a new stub task either to stdout, or path",
                  "args allow stubbing a config file, cli parameter, or action",
                  ]

    @property
    def param_specs(self) -> list:
        return [
            *super().param_specs,
            self.build_param(prefix="--", name="strang",  type=bool,    default=False,           desc="Generate a stub strang/location expansion"),
            self.build_param(name="suppress-header",  default=True, implicit=True),
            ]

    def __call__(self, tasks:ChainGuard, plugins:ChainGuard):
        match dict(doot.args.cmd.args):
            case {"config": True}:
                self._stub_doot_toml()
            case {"action": True}:
                result = self._stub_action(plugins)
                self._print_text(result)
            case {"param": True}:
                result = self._stub_cli_param()
                self._print_text(result)
            case {"printer": True}:
                result = self._stub_printer()
                self._print_text(result)
            case _:
                result = self._stub_task_toml(tasks, plugins)
                self._print_text(result)

    def _print_text(self, text:list[ListVal]) -> None:
        for line in text:
            match line:
                case str():
                    cmd_l.user(line)
                case (str() as s, dict() as d):
                    cmd_l.user(s, extra=d)
                case None:
                    cmd_l.user("")
