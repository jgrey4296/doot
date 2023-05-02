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

from doot import globber
from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.json import JsonMixin
from doot.mixins.plantuml import PlantUMLMixin

class JsonPythonSchema(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, FilerMixin, CommanderMixin, JsonMixin):
    """
    ([data] -> codegen) Use XSData to generate python bindings for a directory of json's
    """

    def __init__(self, name="report::json.schema.py", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
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
            "clean"    : [ (self.rmdirs, [gen_package]) ],
            "actions"  : [
                self.make_xsdata_config(),
                self.make_cmd(self.json_schema, fpath, gen_package),
            ]
        })
        return task

class JsonVisualise(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, JsonMixin, PlantUMLMixin):
    """
    ([data] -> visual) Wrap json files with plantuml header and footer,
    ready for plantuml to visualise structure
    """

    def __init__(self, name="report::json:.schema.img", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".json"], rec=rec)
        self.locs.ensure("build", "temp", task=name)

    def set_params(self):
        return self.target_params() + self.plantuml_params()

    def subtask_detail(self, task, fpath):
        dst = self.locs.temp / fpath.with_stem(task['name']).name
        img = self.locs.build / "json" / fpath.stem
        task.update({
            "targets"  : [ img ],
            "actions"  : [ (self.json_plantuml, [dst, fpath]),
                          (self.plantuml_img, [img, dst]),
                          ]
            })
        return task
