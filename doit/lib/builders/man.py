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

import doot
from doot.tasker import DootTasker
from doot.mixins.commander import CommanderMixin

class ManBuild(DootTasker, CommanderMixin):
    """
    Convert markdown to man format and install
    """

    def __init__(self, name="man::build", locs=None):
        super().__init__(name, locs)
        locs.ensure("man", "man_markdown")

    def task_detail(self, task):
        task.update({
            "actions": [ self.compile_cmd ],
            "pos_arg" : "targs",

        })
        return task

    def compile_cmd(self, targs):
        for target in targs:
            source = self.locs.man_markdown / target
            if not source.exists():
                logging.warning("Manpage Markdown target doesn't exist: %s", source)
                continue

            result = re.search(f"\.(\d+)\.md", target)
            if not result:
                logging.warning("Unrecognized man page target group: %s", target)
                continue

            group_num = result[1]
            out_dir = self.locs.man / f"man{group_num}"
            out_dir.mkdir(exist_ok=True)

            out_file = out_dir / source.with_suffix("").name

            logging.info("Compiling: %s -> %s", source, out_file)
            cmd = self.cmd("pandoc", source, "-s", "-t", "man", "-o", out_file)
            cmd.execute()
            logging.info(cmd.out)
            logging.info(cmd.err)
