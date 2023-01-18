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
    godot_dirs = doot.locs.extend(name="godot", _src="")
    godot_dirs.update({ "scenes" : godot_dirs.src / "scenes",
                      })

    godot_group += godot.GodotBuild(dirs=godot_dirs)
    godot_group += godot.GodotRunScene(dirs=godot_dirs, roots=[godot_dirs.src])
    godot_group += godot.GodotRunScript(dirs=godot_dirs, roots=[godot_dirs.src])
    godot_group += godot.task_godot_version
    godot_group += godot.task_godot_test
    godot_group += godot.task_newscene(godot_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False, bool).tool.doot.group.godot.debug():
        print("To activate group godot needs: ", err)
##-- end godot

##-- xml
xml_group = TaskGroup("xml_group")
try:
    doot.config.tool.doot.group.xml
    xml_dirs = doot.locs.extend(name="xml")
    xml_dirs.update({"visual": xml_dirs.docs / "visual",
                        "elements" : xml_dirs.build / "elements",
                        "schema"    : xml_dirs.build / "schema",

                        })
    from doot.taskslib.data import xml as xml_reports

    xml_group += xml_reports.XmlElementsTask(dirs=xml_dirs)
    xml_group += xml_reports.XmlSchemaTask(dirs=xml_dirs)
    xml_group += xml_reports.XmlPythonSchemaRaw(dirs=xml_dirs)
    xml_group += xml_reports.XmlPythonSchemaXSD(dirs=xml_dirs)
    xml_group += xml_reports.XmlSchemaVisualiseTask(dirs=xml_dirs)
    xml_group += xml_reports.XmlFormatTask(dirs=xml_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False, bool).tool.doot.group.xml.debug():
        print("To activate group, xml needs: ", err)
##-- end xml

##-- sqlite
sqlite_group = TaskGroup("sqlite_group")
try:
    doot.config.tool.doot.group.database
    from doot.taskslib.data import database
    sqlite_dirs  = doot.locs.extend(name="sqlite")

    sqlite_group += database.SqliteReportTask(dirs=sqlite_dirs)
    sqlite_group += database.SqlitePrepTask(dirs=sqlite_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False, bool).tool.doot.group.database.debug():
        print("To activate group, sqlite needs: ", err)

##-- end sqlite

##-- json
json_group = TaskGroup("json group")
try:
    doot.config.tool.doot.group.json
    from doot.taskslib.data import json as json_reports
    json_dirs = doot.locs.extend(name="json")
    json_dirs.update({
        "visual" : json_dirs.build / "visual"
    })
    # from doot.taskslib.docs.plantuml import task_plantuml_json

    json_group += json_reports.JsonPythonSchema(dirs=json_dirs)
    json_group += json_reports.JsonFormatTask(dirs=json_dirs)
    json_group += json_reports.JsonVisualise(dirs=json_dirs)
    # json_group += json_reports.JsonSchemaTask()
    #
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False, bool).tool.doot.group.json.debug():
        print("To activate group, json needs: ", err)
##-- end json

##-- plantuml
plantuml_group = TaskGroup("plantuml_group")
try:
    doot.config.tool.doot.group.plantuml
    from doot.taskslib.docs import plantuml
    plant_dirs = doot.locs.extend(name="plantuml", _src="docs/visual")
    plant_dirs.update({
        "visual" : plant_dirs.build / "visual"
    })

    plantuml_group += plantuml.PlantUMLGlobberTask(dirs=plant_dirs)
    plantuml_group += plantuml.PlantUMLGlobberTask(dirs=plant_dirs)
    plantuml_group += plantuml.PlantUMLGlobberCheck(dirs=plant_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False, bool).tool.doot.group.plantuml.debug():
        print("To activate group, plantuml needs: ", err)

##-- end plantuml

##-- csv
csv_group = TaskGroup("csv group")
try:
    doot.config.tool.doot.group.csv
    csv_dirs = doot.locs.extend(name="csv")
    from doot.taskslib.data import csv as csv_reports

    csv_group += csv_reports.CSVSummaryTask(dirs=csv_dirs)
    csv_group += csv_reports.CSVSummaryXMLTask(dirs=csv_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False, bool).tool.doot.group.csv.debug():
        print("To activate group, csv needs: ", err)

##-- end csv

##-- dot
dot_group = TaskGroup("dot group")
try:
    doot.config.tool.doot.group.dot
    dot_dirs = doot.locs.extend(name="dot", _src="docs/visual")
    from doot.taskslib.docs import dot
    dot_group += dot.DotVisualise(dirs=dot_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False, bool).tool.doot.group.dot.debug():
        print("To activate group, dot needs: ", err)

##-- end dot

##-- images
images_group = TaskGroup("images group")
try:
    doot.config.tool.doot.group.images
    image_dirs  = doot.locs.extend(name="images")
    from doot.taskslib.data import images
    images_group += images.HashImages(dirs=image_dirs)
    images_group += images.OCRGlobber(dirs=image_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False, bool).tool.doot.group.images.debug():
        print("To activate group, images needs: ", err)

##-- end images

##-- repls

repls_group = TaskGroup("repls group")
try:
    doot.config.tool.doot.group.repls.py
    from doot.taskslib.cli import basic_repls
    repls_group += basic_repls.task_pyrepl

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False, bool).tool.doot.group.repls.debug():
        print("To activate python repl, needs: ", err)

try:
    doot.config.tool.doot.group.repls.prolog
    from doot.taskslib.cli import basic_repls
    repls_group += basic_repls.task_prolog_repl

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False, bool).tool.doot.group.repls.debug():
        print("To activate prolog repl, needs: ", err)

##-- end repls
