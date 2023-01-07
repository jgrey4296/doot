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
from doot.utils.task_group import TaskGroup
from doot.utils.toml_access import TomlAccessError, TomlAccess
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
    from doot.builders import godot
    godot_dirs = doot.locs.extend(prefix="godot", _src="")
    godot_dirs.add_extra({ "scenes" : godot_dirs.src / "scenes",
                         })

    godot_group += godot.GodotBuild(godot_dirs)
    godot_group += godot.GodotRunScene(godot_dirs, [godot_dirs.src])
    godot_group += godot.GodotRunScript(godot_dirs, [godot_dirs.src])
    godot_group += godot.task_godot_version
    godot_group += godot.task_godot_test
    godot_group += godot.task_newscene(godot_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.announce_groups():
        print("To activate group godot needs: ", err)
##-- end godot

##-- xml
xml_group = TaskGroup("xml_group")
try:
    doot.config.tool.doot.group.xml
    xml_dirs = doot.locs.extend(prefix="xml")
    xml_dirs.add_extra({"visual": xml_dirs.docs / "visual",
                        "elements" : xml_dirs.build / "elements",
                        "schema"    : xml_dirs.build / "schema",

                        })
    xml_data_dirs = [xml_dirs.data] + [pl.Path(x) for x in doot.config.or_get([]).tool.doot.xml.data_dirs() if pl.Path(x).exists()]
    from doot.data import xml as xml_reports

    xml_group += xml_reports.XmlElementsTask(xml_dirs, xml_data_dirs)
    xml_group += xml_reports.XmlSchemaTask(xml_dirs, xml_data_dirs)
    xml_group += xml_reports.XmlPythonSchemaRaw(xml_dirs, xml_data_dirs)
    xml_group += xml_reports.XmlPythonSchemaXSD(xml_dirs, xml_data_dirs)
    xml_group += xml_reports.XmlSchemaVisualiseTask(xml_dirs, xml_data_dirs)
    xml_group += xml_reports.XmlFormatTask(xml_dirs, xml_data_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.announce_groups():
        print("To activate group, xml needs: ", err)
##-- end xml

##-- sqlite
sqlite_group = TaskGroup("sqlite_group")
try:
    doot.config.tool.doot.group.databse
    from doot.data import database
    sqlite_dirs  = doot.locs.extend(prefix="sqlite")

    sqlite_group += database.SqliteReportTask(sqlite_dirs)
    sqlite_group += database.SqlitePrepTask(sqlite_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.announce_groups():
        print("To activate group, sqlite needs: ", err)

##-- end sqlite

##-- json
json_group = TaskGroup("json group")
try:
    doot.config.tool.doot.group.json
    from doot.data import json as json_reports
    data_dirs = [pl.Path(x) for x in doot.config.or_get([]).tool.doot.json.data_dirs() if pl.Path(x).exists()]
    json_dirs = doot.locs.extend(prefix="json")
    # from doot.docs.plantuml import task_plantuml_json

    json_group += json_reports.JsonPythonSchema(data_dirs)
    json_group += json_reports.JsonFormatTask(data_dirs, json_gen_dir)
    json_group += json_reports.JsonVisualise(data_dirs, visual_dir)
    # json_group += json_reports.JsonSchemaTask()
    #
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.announce_groups():
        print("To activate group, json needs: ", err)
##-- end json

##-- plantuml
plantuml_group = TaskGroup("plantuml_group")
try:
    doot.config.tool.doot.group.plantuml
    from doot.docs import plantuml
    plant_dirs = doot.locs.extend(prefix="plantuml", _src="docs/visual")

    plantuml_group += plantuml.PlantUMLGlobberTask(dirs, [plant_dirs.src], plant_dir)
    plantuml_group += plantuml.PlantUMLGlobberTask(dirs, [plant_dirs.src], plant_dir, fmt="txt")
    plantuml_group += plantuml.PlantUMLGlobberCheck(dirs, [plant_dirs.src])

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.announce_groups():
        print("To activate group, plantuml needs: ", err)


##-- end plantuml

##-- csv
csv_group = TaskGroup("csv group")
try:
    doot.config.tool.doot.group.csv
    csv_dirs = doot.locs.extend(prefix="csv")
    from doot.data import csv as csv_reports
    csv_group += csv_reports.CSVSummaryTask(csv_dirs, [csv_dirs.data])
    csv_group += csv_reports.CSVSummaryXMLTask(csv_dirs, [csv_dirs.data], csv_dir)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.announce_groups():
        print("To activate group, csv needs: ", err)

##-- end csv

##-- dot
dot_group = TaskGroup("dot group")
try:
    doot.config.tool.doot.group.dot
    dot_dirs = doot.locs.extend(prefix="dot", _src="docs/visual")
    from doot.docs import dot
    dot_group += dot.DotVisualise(dot_dirs, [dot_dirs.src])

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.announce_groups():
        print("To activate group, dot needs: ", err)

##-- end dot

##-- images
images_group = TaskGroup("images group")
try:
    doot.config.tool.doot.group.images
    image_dirs  = doot.locs.extend(prefix="images")
    image_roots = [pl.Path(x) for x in doot.config.or_get([]).tool.doot.images.data_dirs() if pl.Path(x).exists()]
    from doot.data import images
    images_group += images.HashImages(image_dirs, image_roots)
    images_group += images.OCRGlobber(image_dirs, image_roots)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.announce_groups():
        print("To activate group, images needs: ", err)

##-- end images

##-- repls

repls_group = TaskGroup("repls group")
try:
    doot.config.tool.doot.group.repls.py
    from doot.cli import basic_repls
    repls_group += basic_repls.task_pyrepl

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.announce_groups():
        print("To activate python repl, needs: ", err)

try:
    doot.config.tool.doot.group.repls.prolog
    from doot.cli import basic_repls
    repls_group += basic_repls.task_prolog_repl

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.announce_groups():
        print("To activate prolog repl, needs: ", err)

##-- end repls
