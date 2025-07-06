#!/usr/bin/env python3
"""

"""
# mypy: disable-error-code="attr-defined"
# ruff: noqa: B009
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
from collections import defaultdict
from copy import deepcopy
from importlib.resources import files
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Mixin, Proto
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.util.dkey import DKey
from doot.util.dkey import DKeyed
from doot.workflow.job import DootJob
from doot.workflow.structs.task_name import TaskName
from doot.workflow.task import DootTask

# ##-- end 1st party imports

# ##-| Local
from ._base import BaseCommand
from .structs import TaskStub

# # End of Imports.

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe, Lambda
    from jgdv.structs.chainguard import ChainGuard
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    type ListVal = str|Lambda|tuple[str,dict]

##--|
from doot.control.loaders._interface import PluginLoader_p
from doot.workflow._interface import Task_p
from ._interface import Command_p
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

##-- data
data_path = files(doot.constants.paths.TEMPLATE_PATH).joinpath(doot.constants.paths.TOML_TEMPLATE) # type: ignore[attr-defined]
##-- end data

PRINT_LOCATIONS : Final[list[str]] = doot.constants.printer.PRINT_LOCATIONS # type: ignore[attr-defined]
NL = None
##--|

class _StubDoot_m:
    """ Mixin for stubbing the doot.toml file """

    def param_specs(self:Command_p) -> list:
        return [
            *super().param_specs(), # type: ignore[safe-super]
            self.build_param(name="--config", type=bool, default=False, desc="Stub a doot.toml"), # type: ignore[attr-defined]
        ]

    def _stub_doot_toml(self) -> list[str]:
        logging.info("---- Stubbing Doot Toml")
        doot_toml = pl.Path("doot.toml")
        data_text = data_path.read_text()
        if doot_toml.exists():
            return [
                data_text,
                "# doot.toml it already exists, printed to stdout instead",
            ]

        with doot_toml.open("a") as f:
            f.write(data_text)

        doot.report.user("doot.toml stub")
        return []

class _StubParam_m:
    """ Mixin for stubbing a cli parameter """

    def param_specs(self) -> list:
        return [
            *super().param_specs(), # type: ignore[misc]
            self.build_param(name="--param", type=bool, default=False, desc="Generate a stub cli arg dict"),
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
    """ Mixin for stubbing an action """

    def param_specs(self) -> list:
        return [
            *super().param_specs(), # type: ignore[misc]
            self.build_param(name="--action", type=bool, default=False, desc="Help Stub Actions"),
        ]

    def _stub_action(self, plugins:ChainGuard) -> list[Maybe[str]]:
        logging.info("---- Stubbing Actions")
        result : list[Maybe[str]] = []
        target_name = doot.args.cmd.args.name
        unaliased = doot.aliases.on_fail(target_name).action[target_name]
        matched = [x for x in plugins.action
                   if x.name == target_name
                   or x.value == unaliased]
        if bool(matched):
            loaded = matched[0].load()
            result.append(f"- {matched[0].name} (Action, {matched[0].value})")
            match getattr(loaded, "_toml_help", []):
                case [] if bool(getattr(loaded, "__doc__")):
                    result.append(loaded.__doc__)
                case []:
                    pass
                case [*xs]:
                    for x in xs:
                        result.append(x)

            loaded = getattr(loaded, "__call__", loaded)  # noqa: B004
            match DKeyed.get_keys(loaded):
                case []:
                    result.append("-- No Declared Kwargs")
                case [*xs]:
                    result += [
                        "-- Declared kwargs for action:",
                        *(f"---- {x!r}" for x in sorted(xs, key=lambda x: repr(x))),
                    ]

        result.append(NL)
        result.append("-- Toml Form of an action: ")
        # TODO customize this with declared annotations
        if bool(matched):
            result.append(f"{{ do=\"{matched[0].name}\", args=[], key=val }} ")
        else:
            result.append("{ do=\"action name/import path\", args=[]} # plus any kwargs a specific action uses")

        return result

class _StubTask_m:
    """ Mixin for stubbing a task """

    def param_specs(self) -> list:
        return [
            *super().param_specs(), # type: ignore[misc]
            self.build_param(name="--task", type=bool, desc="Stub a Task Specification"),
            self.build_param(name="-out",   type=str, default="", desc="If set, append the stub to this file"),

            self.build_param(name="<1>name", type=str, default=None,    desc="The Name of the new task"),
            self.build_param(name="<2>ctor", type=str, default="task",  desc="a code ref, or alias of a task class"),
        ]

    def _stub_task_toml(self, tasks, plugins) -> list[str]:  # noqa: PLR0912
        """
        This creates a toml stub using default values, as best it can
        """
        logging.info("---- Stubbing Task Toml")
        result = []

        # Create stub toml, with some basic information
        stub                  = TaskStub()
        stub['name'].default  = self._stub_task_name(tasks)
        self._add_ctor_specific_stub_fields(stub)

        # Output to doot.report/stdout, or file
        if doot.args.cmd.args.out == "":
            result.append(stub.to_toml())
            return result

        task_file = pl.Path(doot.args.cmd.args.out)
        if task_file.is_dir():
            task_file /= "stub_tasks.toml"
        doot.report.user("Stubbing task %s into file: %s", stub['name'], task_file)
        with task_file.open("a") as f:
            f.write("\n")
            f.write(stub.to_toml())

        return []

    def _stub_task_name(self, tasks):
        match doot.args.on_fail(None).cmd.args.name():
            case None:
                raise doot.errors.CommandError("No Name Provided for Stub")
            case x:
                name = TaskName(x)

        # extend the name if there are already tasks with that name
        original_name = name
        count = 0
        while str(name) in tasks:
            count += 1
            name = original_name.push("$conflicted$", count)
        else:
            return name

    def _add_ctor_specific_stub_fields(self, stub:TaskStub) -> None:
        """ add ctor specific fields,
        such as for dir_walker: roots [], exts [], recursive bool, subtask "", head_task ""
        works *towards* the task_type, not away, so more specific elements are added over the top of more general elements
        """
        match  doot.aliases.task.get((ctor:=doot.args.on_fail("task").cmd.args.ctor()), None):
            case None:
                raise doot.errors.CommandError("Task Ctor was not appliable", ctor)
            case x:
                task_ctor : CodeReference = CodeReference(x)

        try:
            match task_ctor():
                case type() as ctor:
                    task_mro = ctor.mro()
                case Exception() as err:
                    raise err
        except TypeError as err:
            logging.exception(err.args[0].replace("\n", ""))
            task_mro = []
            return

        for cls in reversed(task_mro):
            try:
                cls.stub_class(stub)
                if isinstance(cls, Task_p):
                    stub['doot_version'].default         = doot.__version__
                    stub['doc'].default             = []
            except NotImplementedError:
                pass
            except AttributeError:
                pass

        # Convert to aliases
        stub['ctor'].default   = task_ctor

class _StubPrinter_m:
    """
    Mixin for stubbing printer config
    """

    def param_specs(self) -> list:
        return [
            *super().param_specs(), # type: ignore[misc]
            self.build_param(name="--doot.report", type=bool, default=False, desc="Generate a stub doot.report config"),
        ]

    def _stub_printer(self) -> list[Maybe[str|tuple]]:
        logging.info("---- Printing Printer Spec Info")
        result = [
            ("- Printer Config Spec Form. Use in doot.toml [logging], [logging.subprinters], and [logging.extra]", {"colour":"blue"}),
            NL,
            'NAME = { level="", filter=[], target=[""], format="", colour=true, propagate=false, filename_fmt=""}',
        ]
        return result

##--|

@Proto(Command_p)
@Mixin(_StubDoot_m, _StubParam_m, _StubAction_m, _StubTask_m, _StubPrinter_m)
class StubCmd(BaseCommand):
    """ Called to interactively create a stub task definition
      with a `target`, outputs to that file, else to stdout for piping
    """
    _name : ClassVar[str]           = "stub" # type: ignore[misc]
    _help : ClassVar[list[str]]     = ["Create a new stub task either to stdout, or path",
                                       "args allow stubbing a config file, cli parameter, or action",
                                       ]

    def param_specs(self) -> list:
        return [
            *super().param_specs(),
            self.build_param(name="--strang", type=bool, default=False, desc="Generate a stub strang/location expansion"),
            self.build_param(name="--suppress-header",  default=True, implicit=True),
        ]

    def __call__(self, tasks:ChainGuard, plugins:ChainGuard):
        match dict(doot.args.cmd.args):
            case {"config": True}:
                result = self._stub_doot_toml()
            case {"action": True}:
                result = self._stub_action(plugins)
            case {"param": True}:
                result = self._stub_cli_param()
            case {"doot.report": True}:
                result = self._stub_printer()
            case _:
                result = self._stub_task_toml(tasks, plugins)
        ##--|
        self._print_text(result)
