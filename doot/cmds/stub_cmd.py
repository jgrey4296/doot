#!/usr/bin/env python3
"""

"""
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
from jgdv import Proto, Mixin
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.enums
import doot.errors
from doot._structs.dkey import DKey
from doot.cmds.core.cmd import BaseCommand
from doot.structs import DKeyed, TaskName, TaskStub
from doot.task.core.job import DootJob
from doot.task.core.task import DootTask

# ##-- end 1st party imports

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
    from jgdv import Maybe, ChainGuard, Lambda
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    type ListVal = str|Lambda|tuple[str,dict]

##--|
from doot._abstract import PluginLoader_p, Task_p, Command_p
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

##-- data
data_path = files(doot.constants.paths.TEMPLATE_PATH).joinpath(doot.constants.paths.TOML_TEMPLATE)
##-- end data

PRINT_LOCATIONS : Final[list[str]] = doot.constants.printer.PRINT_LOCATIONS
NL = None
##--|

class _StubDoot_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(name="--config", type=bool, default=False, desc="Stub a doot.toml"),
                ]

    def _stub_doot_toml(self) -> list[str]:
        logging.info("---- Stubbing Doot Toml")
        doot_toml = pl.Path("doot.toml")
        data_text = data_path.read_text()
        if doot_toml.exists():
            doot.report.user(data_text)
            doot.report.user("")
            doot.report.user("- doot.toml it already exists, printed to stdout instead", extra={"colour":"red"})
            return

        with doot_toml.open("a") as f:
            f.write(data_text)

        doot.report.user("doot.toml stub")
        return []

class _StubParam_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
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

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(name="--action", type=bool, default=False, desc="Help Stub Actions"),
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
            result.append("{ do=\"action name/import path\", args=[]} # plus any kwargs a specific action uses")

        return result

class _StubTask_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(name="--task", type=bool),
                self.build_param(name="-out",   type=str, default=""),

                self.build_param(name="<1>name", type=str, default=None,    desc="The Name of the new task"),
                self.build_param(name="<2>ctor", type=str, default="task",  desc="a code ref, or alias of a task class"),
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
                if issubclass(cls, Task_p):
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

class _StubPrinter_m:

    @property
    def param_specs(self) -> list:
        return [*super().param_specs,
                self.build_param(name="--doot.report", type=bool, default=False, desc="Generate a stub doot.report config"),
                ]

    def _stub_printer(self) -> list[str]:
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
    _name      = "stub"
    _help      = ["Create a new stub task either to stdout, or path",
                  "args allow stubbing a config file, cli parameter, or action",
                  ]

    @property
    def param_specs(self) -> list:
        return [
            *super().param_specs,
            self.build_param(name="--strang", type=bool, default=False, desc="Generate a stub strang/location expansion"),
            self.build_param(name="--suppress-header",  default=True, implicit=True),
            ]

    def __call__(self, tasks:ChainGuard, plugins:ChainGuard):
        match dict(doot.args.cmd.args):
            case {"config": True}:
                result = self._stub_doot_toml()
                self._print_text(result)
            case {"action": True}:
                result = self._stub_action(plugins)
                self._print_text(result)
            case {"param": True}:
                result = self._stub_cli_param()
                self._print_text(result)
            case {"doot.report": True}:
                result = self._stub_printer()
                self._print_text(result)
            case _:
                result = self._stub_task_toml(tasks, plugins)
                self._print_text(result)
