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

from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin

class JsonPythonSchema(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, FilerMixin, CommanderMixin):
    """
    ([data] -> codegen) Use XSData to generate python bindings for a directory of json's
    """

    def __init__(self, name="json::schema.python", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".json"], rec=rec)
        self.locs.ensure("codegen", task=name)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.globc.accept
        return self.globc.discard

    def subtask_detail(self, task, fpath=None):
        gen_package = str(self.locs.codegen / task['name'])
        task.update({
            "targets"  : [ gen_package ],
            "task_dep" : [ "_xsdata::config" ],
            "clean"    : [ (self.rmdirs, [gen_package]) ],
            "actions"  : [ self.make_cmd(self.generate_on_target, fpath, gen_package) ]
        })
        return task

    def generate_on_target(self, fpath, gen_package, task):
        args = ["xsdata", "generate",
                ("--recursive" if not self.rec else ""),
                "-p", gen_package,
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                fpath
                ]

        return args

class JsonVisualise(DelayedMixin, TargetedMixin, globber.DootEagerGlobber):
    """
    ([data] -> visual) Wrap json files with plantuml header and footer,
    ready for plantuml to visualise structure
    """

    def __init__(self, name="json::schema.visual", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".json"], rec=rec)
        self.locs.ensure("visual", task=name)

    def set_params(self):
        return self.target_params()

    def subtask_detail(self, task, fpath=None):
        task.update({
            "targets"  : [ self.locs.visual / fpath.with_stem(task['name']).name ],
            "actions"  : [ (self.write_plantuml, [fpath]) ]
            })
        return task

    def write_plantuml(self, fpath, targets):
        header   = "@startjson\n"
        footer   = "\n@endjson\n"

        with open(pl.Path(targets[0]), 'w') as f:
            f.write(header)
            f.write(fpath.read_text())
            f.write(footer)
