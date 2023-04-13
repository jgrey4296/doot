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

from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin

class XmlElementsTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """
    ([data] -> elements) xml element retrieval using xml starlet toolkit
    http://xmlstar.sourceforge.net/
    """

    def __init__(self, name="xml::elements", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".xml"], rec=rec)
        self.locs.ensure("elements", task=name)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath:dict=None) -> dict:
        task.update({
            "targets" : [ self.locs.elements / (task['name'] + ".elements")],
            "clean"   : True,
            "actions" : [ self.make_cmd(self.generate_on_target, fpath, save="elements"),
                          (self.write_to, [fpath, "elements"]),
                         ]
        })
        return task

    def generate_on_target(self, fpath, targets, task):
        """
        build an `xml el` command of all available xmls
        """
        globbed = self.glob_target(fpath, fn=lambda x: x.is_file())
        return ["xml", "el", "-u", *globbed]

class XmlSchemaTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """
    ([data] -> schema) Generate .xsd's from directories of xml files using trang
    https://relaxng.org/jclark/
    """

    def __init__(self, name="xml::schema", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".xml"], rec=rec)
        self.locs.ensure("schema", task=name)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        task.update({
            "targets"  : [ self.locs.schema / (task['name'] + ".xsd") ],
            "clean"    : True,
            "uptodate" : [True],
            "actions"  : [self.make_cmd(self.generate_on_target, fpath)],
            })
        return task

    def generate_on_target(self, fpath, targets, task):
        globbed = self.glob_target(fpath, fn=lambda x: x.is_file())
        return ["trang", *globbed, *targets]

class XmlPythonSchemaRaw(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """
    ([data] -> codegen) Generate Python Dataclass bindings based on raw XML data
    """

    def __init__(self, name="xml::schema.python.raw", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".xml"], rec=rec)
        self.locs.ensure("codegen", task=name)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        gen_package = str(self.locs.codegen / task['name'])
        task.update({
            "targets"  : [ gen_package ],
            "task_dep" : [ "_xsdata::config"],
            "actions"  : [ self.make_cmd(self.generate_on_target, fpath, gen_package) ],
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
                fpath,
                ]
        return args

class XmlPythonSchemaXSD(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """
    ([data] -> codegen) Generate python dataclass bindings from XSD's
    """

    def __init__(self, name="xml::schema.python.xsd", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".xsd"], rec=rec)
        self.locs.ensure("build", "codegen", task=name)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        gen_package = str(self.locs.codegen / task['name'])
        task.update({
            "targets"  : [ gen_package ],
            "file_dep" : [ fpath ],
            "task_dep" : [ "_xsdata::config"],
            "actions"  : [self.make_cmd(self.gen_target, fpath, gen_package) ],
            })
        return task

    def gen_target(self, fpath, gen_package, task):
        args = ["xsdata", "generate",
                ("--recursive" if not self.rec else ""),
                "-p", gen_package,
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                fpath,
                ]

        return args

class XmlSchemaVisualiseTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """
    ([data] -> visual) Generate Plantuml files ready for plantuml to generate images
    """

    def __init__(self, name="xml::schema.plantuml", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".xsd"], rec=rec)
        self.locs.ensure("visual", task=name)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        task.update({
            "targets"  : [ self.locs.visual / (task['name'] + ".plantuml") ],
            "file_dep" : [ fpath ],
            "task_dep" : [ "_xsdata::config" ],
            "actions" : [self.make_cmd("xsdata", "generate", "-o", "plantuml", "-pp", fpath, save="result")
                         (self.write_to, [fpath, "result"])
                         ],
            "clean"    : True,
            })
        return task
