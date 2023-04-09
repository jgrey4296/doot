#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Final)
from uuid import UUID, uuid1
from weakref import ref

import doot
from doot.tasker import DootTasker
from doot.mixins.commander import CommanderMixin

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

collect_libs  : Final[list] = doot.config.on_fail([], list).python.compile.collect()

class TODOPythonCompile(DootTasker, CommanderMixin):
    """
    https://pyinstaller.org/en/stable/
    Use pyinstaller to create an exe
    pyinstaller --collect-all tkinterdnd2 -w sub_processor.py
    """

    def __init__(self, name="python::compile", locs=None):
        super().__init__(name, locs)
        self.locs.ensure("build", "temp", "src", task=name)

    def set_params(self):
        return [
            { "name" : "output",
                "short" : "o",
                "type" : str,
                "default": "--onedir",
                "choices" : [("--onefile", ""),
                             ("--onedir", ""),

                             ],
              }
        ]

    def task_detail(self, task):
        task.update({
            "actions" : [ self.make_cmd(self.build_cmd) ],
        })
        return task

    def build_cmd(self):
        args = [ "pyinstaller",
                 "--distpath", self.locs.build,
                 "--workpath", self.locs.temp,
                 "--name", self.locs.src.name,
                 ]
        # TODO --add-data
        # TODO --paths

        if bool(collect_libs):
            args.append("--collect-all")
            args += collect_libs
        args.append("-w")
        args.append(self.locs.src)
        return args
