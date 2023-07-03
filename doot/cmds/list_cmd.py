
#!/usr/bin/env python3
"""

"""
##-- imports
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

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

import doot
import doot.errors
from doot._abstract.cmd import Command_i
from collections import defaultdict


class ListCmd(Command_i):
    _name      = "list"
    _help      = ["A simple command to list all loaded task heads."]
    STATUS_MAP = {'ignore': 'I', 'up-to-date': 'U', 'run': 'R', 'error': 'E'}

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            self.make_param(name="all", default=True),
            self.make_param(name="dependencies", default=False),
            self.make_param(name="target", type=str, default=""),
            ]



    def __call__(self, tasks, plugins):
        """List task generators"""
        logging.debug("Starting to List Taskers/Tasks")

        if doot.args.cmd.args.help:
            printer.info(self.help)
            return

        if doot.args.cmd.args.target == "" and not doot.args.cmd.args.all:
            raise ValueError("ListCmd Needs a target, or all")

        # load reporter
        if 'reporter' not in plugins or not bool(plugins['reporter']):
            raise doot.errors.DootPluginError("Missing Reporter Plugin")

        if not bool(tasks):
            printer.info("No Tasks Defined")
            return

        if doot.args.cmd.args.all: # print all tasks

            printer.info("Defined Task Generators:")
            for key, (desc, cls) in tasks.items():
                logging.info("%s (%s) : %s", key, cls, desc)

            return

        # print specific tasks
        assert(doot.args.cmd.args.target != "")
        target = doot.args.cmd.args.target
        matches = {x for x in tasks.keys() if target.lower() in x.lower()}
        printer.info("Tasks for Target: %s", target)
        for x in matches:
            (desc, cls) = tasks[x]
            printer.info("%s (%s) : %s", x, cls, desc)
        return
