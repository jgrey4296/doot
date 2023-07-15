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
from doot._abstract.cmd import Command_i
from doot._abstract.parser import DootParamSpec
from collections import defaultdict

class StubCmd(Command_i):
    """ Called to interactively create a stub task definition
      with a `target`, outputs to that file, else to stdout for piping
    """
    _name      = "stub"
    _help      = ["Create a new stub task either to stdout, or path"]

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            self.make_param("name", type=str, default="stub", desc="The Name of the new task"),
            self.make_param("type", type=str, default="basic", desc="the short type name of the task generator"),
            self.make_param("class", type=str, default="", desc="full class import name of the task generator"),
            self.make_param("group", type=str, default="stubbed"),
            self.make_param("file-target", type=str, default=""),
            self.make_param("suppress-header", default=True, invisible=True)
            ]

    def __call__(self, tasks:Tomler, plugins:Tomler):

        task_type, task_class = None, None
        match dict(doot.args.cmd.args):
            case { "type": x, "class": "" } if x in set(map(lambda x: x.name, plugins.tasker)):
                task_type = x
            case { "type": x, "class": "" }:
                raise TypeError("Task 'type' needs to be one of: ", set(map(lambda x: x.name, plugins.tasker)))
            case { "type": "", "class": x } if x != "":
                task_class = x
            case _:
                raise TypeError("Task must have a type or class")

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


class StubConfigCmd(Command_i):
    """ Called to stub a doot.toml """
    pass
