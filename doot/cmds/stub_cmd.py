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


import doot
import doot.constants
from doot._abstract.cmd import Command_i
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
            self.make_param("class",       type=str,     default="",        desc="Full class import name of the task generator"),
            self.make_param("Config",                    default=False,     desc="Sub a doot.toml",                  prefix="--"),
            self.make_param("Types",                     default=False,     desc="List the types of task available", prefix="--"),
            self.make_param("group", type=str, default="stubbed"),
            self.make_param("name",        type=str,     default="stub",    desc="The Name of the new task",                   positional=True),
            self.make_param("group",       type=str,     default="stubbed", desc="The group the stubbed task will be part of", positional=True),
            self.make_param("type",        type=str,     default="basic",   desc="The short type name of the task generator",  positional=True),
            self.make_param("suppress-header",           default=True, invisible=True)
            ]

    def __call__(self, tasks:Tomler, plugins:Tomler):
        match dict(doot.args.cmd.args):
            case {"Types": True}:
                self._print_types(plugins)
            case {"Config": True}:
                self._stub_doot_toml()
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

        printer.info("doot.toml stubbed")

    def _stub_task_toml(self, tasks, plugins):
        logging.info("Building Task Toml Stub")
        task_type, task_class = None, None
        match dict(doot.args.cmd.args):
            case { "class": x } if bool(x):
                task_class = x
            case { "type": x } if x in set(map(lambda x: x.name, plugins.tasker)):
                task_type = x
            case { "type": x, "class": "" }:
                raise doot.errors.DootParseError("Bad Task 'type': \"%s\". Should be one of: %s", x, set(map(lambda x: x.name, plugins.tasker)))
            case _:
                raise doot.errors.DootParseError("Task must have a type or class\n %s", dict(doot.args.cmd.args))

        stub_name = doot.args.cmd.args.name
        while stub_name in tasks:
            conflict  = stub_name
            stub_name = f"{conflict}_stub"
            logging.warning("Group %s: Name %s already defined, trying to modify name to: %s",
                            doot.args.cmd.args.group,
                            conflict,
                            stub_name)
        # Create stub toml
        stubbed = []
        stubbed.append(f"[[tasks.{doot.args.cmd.args.group}]] # TODO ")
        stubbed.append(f'name   = "{stub_name}"')
        if task_type:
            stubbed.append(f'type   = "{doot.args.cmd.args["type"]}"')
        else:
            stubbed.append(f'class  = "{doot.args.cmd.args["class"]}"')
        stubbed.append("")

        # Output to printer, or file
        if doot.args.cmd.args.file_target == "":
            printer.info("\n".join(stubbed))
            return

        task_file = pl.Path(doot.args.cmd.args.file_target)
        if task_file.is_dir():
            task_file /= "stub_tasks.toml"
        printer.info("Stubbing task %s into file: %s", stub_name, task_file)
        with open(task_file, "a") as f:
            f.write("\n")
            f.write("\n".join(stubbed))
