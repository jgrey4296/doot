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
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

import doot
from doot.task_group import TaskGroup
from doot.toml_access import TomlAccessError, TomlAccess
from doot.errors import DootDirAbsent

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

__all__ = [
    "godot_group", "xml_group",
    "sqlite_group", "json_group",
    "plantuml_group", "csv_group",
    "dot_group", "images_group",
    "repls_group"
]

##-- godot
godot_group = TaskGroup("godot_group")
try:
    doot.config.tool.doot.group.godot
    from doot.taskslib.builders import godot
    godot_src  = doot.config.on_fail(".").tool.doot.group.godot.src()
    godot_locs = doot.locs.extend(name="godot", src=godot_src)
    godot_locs.update({ "scenes" : godot_locs.src / "scenes",
                      })

    godot_group += godot.GodotBuild(locs=godot_locs)
    godot_group += godot.GodotRunScene(locs=godot_locs, roots=[godot_locs.src])
    godot_group += godot.GodotRunScript(locs=godot_locs, roots=[godot_locs.src])
    godot_group += godot.task_godot_version
    godot_group += godot.task_godot_test
    godot_group += godot.task_newscene(godot_locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.godot.debug():
        print("To activate group godot needs: ", err)
##-- end godot

##-- xml
xml_group = TaskGroup("xml_group")
try:
    doot.config.tool.doot.group.xml
    xml_build = doot.config.on_fail(["build"]).tool.doot.group.xml.build()
    xml_docs  = doot.config.on_fail(["docs"]).tool.doot.group.xml.docs()
    xml_locs = doot.locs.extend(name="xml", build=xml_build, docs=xml_docs)
    xml_locs.update({"visual"   : xml_locs.docs / "visual",
                     "elements" : xml_locs.build / "elements",
                     "schema"   : xml_locs.build / "schema",
                     })
    from doot.taskslib.data import xml as xml_reports

    xml_group += xml_reports.XmlElementsTask(locs=xml_locs)
    xml_group += xml_reports.XmlSchemaTask(locs=xml_locs)
    xml_group += xml_reports.XmlPythonSchemaRaw(locs=xml_locs)
    xml_group += xml_reports.XmlPythonSchemaXSD(locs=xml_locs)
    xml_group += xml_reports.XmlSchemaVisualiseTask(locs=xml_locs)
    xml_group += xml_reports.XmlFormatTask(locs=xml_locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.xml.debug():
        print("To activate group, xml needs: ", err)
##-- end xml

##-- sqlite
sqlite_group = TaskGroup("sqlite_group")
try:
    doot.config.tool.doot.group.database
    from doot.taskslib.data import database
    sqlite_locs  = doot.locs.extend(name="sqlite")

    sqlite_group += database.SqliteReportTask(locs=sqlite_locs)
    sqlite_group += database.SqlitePrepTask(locs=sqlite_locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.database.debug():
        print("To activate group, sqlite needs: ", err)

##-- end sqlite

##-- json
json_group = TaskGroup("json group")
try:
    doot.config.tool.doot.group.json
    from doot.taskslib.data import json as json_reports
    json_visual = doot.config.on_fail(["build/visual"]).tool.doot.group.json.visual()
    json_locs = doot.locs.extend(name="json", visual=json_visual)
    # from doot.taskslib.docs.plantuml import task_plantuml_json

    json_group += json_reports.JsonPythonSchema(locs=json_locs)
    json_group += json_reports.JsonFormatTask(locs=json_locs)
    json_group += json_reports.JsonVisualise(locs=json_locs)
    # json_group += json_reports.JsonSchemaTask()
    #
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.json.debug():
        print("To activate group, json needs: ", err)
##-- end json

##-- plantuml
plantuml_group = TaskGroup("plantuml_group")
try:
    doot.config.tool.doot.group.plantuml
    from doot.taskslib.docs import visual
    plant_src  = doot.config.on_fail("docs/visual").tool.doot.group.plantuml.src()
    plant_visual = doot.config.on_fail(["build/visual"]).tool.doot.group.plantuml.visual()
    plant_locs = doot.locs.extend(name="plantuml", src=plant_src, visual=plant_visual)

    plantuml_group += visual.PlantUMLGlobberTask(locs=plant_locs)
    plantuml_group += visual.PlantUMLGlobberTask(locs=plant_locs)
    plantuml_group += visual.PlantUMLGlobberCheck(locs=plant_locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.plantuml.debug():
        print("To activate group, plantuml needs: ", err)

##-- end plantuml

##-- csv
csv_group = TaskGroup("csv group")
try:
    doot.config.tool.doot.group.csv
    csv_locs = doot.locs.extend(name="csv")
    from doot.taskslib.data import csv as csv_reports

    csv_group += csv_reports.CSVSummaryTask(locs=csv_locs)
    csv_group += csv_reports.CSVSummaryXMLTask(locs=csv_locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.csv.debug():
        print("To activate group, csv needs: ", err)

##-- end csv

##-- dot
dot_group = TaskGroup("dot group")
try:
    doot.config.tool.doot.group.dot
    from doot.taskslib.docs import visual
    dot_src = doot.config.on_fail("docs/visual").tool.doot.group.dot.src()
    dot_locs = doot.locs.extend(name="dot", src=dot_src)
    dot_group += visual.DotVisualise(locs=dot_locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.dot.debug():
        print("To activate group, dot needs: ", err)

##-- end dot

##-- images
images_group = TaskGroup("images group")
try:
    doot.config.tool.doot.group.images
    image_locs  = doot.locs.extend(name="images")
    from doot.taskslib.data import images
    images_group += images.HashImages(locs=image_locs)
    images_group += images.OCRGlobber(locs=image_locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.images.debug():
        print("To activate group, images needs: ", err)

##-- end images

##-- repls

repls_group = TaskGroup("repls group")
try:
    doot.config.tool.doot.group.repls.py
    from doot.taskslib.cli import basic_repls
    repls_group += basic_repls.task_pyrepl

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.repls.debug():
        print("To activate python repl, needs: ", err)

try:
    doot.config.tool.doot.group.repls.prolog
    from doot.taskslib.cli import basic_repls
    repls_group += basic_repls.task_prolog_repl

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.repls.debug():
        print("To activate prolog repl, needs: ", err)

##-- end repls
