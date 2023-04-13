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
from doot.mixins.xml import XMLMixin
from doot.mixins.plantuml import PlantUMLMixin

class XmlElementsTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin, XMLMixin):
    """
    ([data] -> elements) xml element retrieval using xml starlet toolkit
    http://xmlstar.sourceforge.net/
    """

    def __init__(self, name="report::xml.elements", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".xml"], rec=rec)
        self.locs.ensure("build", task=name)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.globc.yes
        return self.globc.noBut

    def subtask_detail(self, task, fpath) -> dict:
        dst     = self.locs.build / (task['name'] + ".elements")
        targets = list(self.glob_target(fpath, rec=False, fn=lambda x: self.globc.yes, exts=self.exts))

        task.update({
            "targets" : [ dst ],
            "clean"   : True,
            "actions" : [
                self.make_cmd(self.xml_elements, targets, save="elements"),
                (self.write_to, [ dst, "elements" ]),
            ]
        })
        return task

class XmlSchemaTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin, XMLMixin):
    """
    ([data] -> schema) Generate .xsd's from directories of xml files using trang
    https://relaxng.org/jclark/
    """

    def __init__(self, name="report::xml.trang", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".xml"], rec=rec)
        self.locs.ensure("build", task=name)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.globc.yes
        return self.globc.noBut

    def subtask_detail(self, task, fpath):
        dst     = self.locs.build / (task['name'] + ".xsd")
        targets = list(self.glob_target(fpath, rec=False, fn=lambda x: self.globc.yes, exts=[".xml"]))
        task.update({
            "targets"  : [dst],
            "clean"    : True,
            "actions"  : [self.make_cmd(self.xml_trang, dst, targets)],
            })
        return task

class XmlPythonSchema(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """
    ([data] -> codegen) Generate Python Dataclass bindings based on raw XML data
    """

    def __init__(self, name="report::xml.schema.py", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".xml"], rec=rec)
        self.locs.ensure("codegen", task=name)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.globc.yes
        return self.globc.noBut

    def subtask_detail(self, task, fpath=None):
        gen_package = str(self.locs.codegen / task['name'])
        task.update({
            "targets"  : [ gen_package ],
            "actions"  : [
                self.make_xsdata_config(),
                self.make_cmd(self.xml_xsdata, gen_package, fpath)
                     ],
            })
        return task

class XmlSchemaVisualiseTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin, PlantUMLMixin):
    """
    ([data] -> visual) Generate Plantuml files ready for plantuml to generate images
    """

    def __init__(self, name="xml::schema.plantuml", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".xsd"], rec=rec)
        self.locs.ensure(build, task=name)

    def set_params(self):
        return self.target_params() + self.plantuml_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.globc.yes
        return self.globc.noBut

    def subtask_detail(self, task, fpath=None):
        dst = self.locs.temp / "plantuml" / (task['name'] + ".plantuml")
        dst.parent.mkdir(parents=True)
        img = self.locs.build / "xml" / (task['name'] + ".plantuml")
        img.parent.mkdir(parents=True)

        task.update({
            "targets"  : [ img ],
            "file_dep" : [ fpath ],
            "actions" : [
                self.make_xsdata_config(),
                self.make_cmd(self.xml_plantuml, fpath, save="result"),
                (self.write_to, [fpath, "result"]),
                (self.plantuml_img, [ img, dst]
            ],
            "clean"    : True,
            })
        return task
